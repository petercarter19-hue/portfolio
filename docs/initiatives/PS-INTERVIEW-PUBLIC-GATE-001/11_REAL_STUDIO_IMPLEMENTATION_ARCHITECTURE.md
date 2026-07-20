# PS-INTERVIEW-PUBLIC-GATE-001 — Real Studio Implementation Architecture (5A light / 5C dark)

_Recorded 2026-07-19 by the Claude/Fable architecture-and-feasibility session on
`work/2026-07-19-interview-gate-24-final-review`. This file is the architecture
record required by `10_REAL_STUDIO_AND_HOMEPAGE_DEMO_CONVERGENCE.md` Gate 2.
Status update: implementation of this architecture **has started and is in
review** on `work/2026-07-19-interview-public-gate-001` (see §0 and
`15_REAL_STUDIO_IMPLEMENTATION_COMPLETION_REPORT.md`); the original
"design and feasibility only" boundary applied to the design-gate phase and
is historical, not current._

Reading order: this file (architecture) → `12_GATE_24_CORRECTION_AND_FEASIBILITY_ADDENDUM.md`
(gate closure + readiness result) → `13_SONNET_IMPLEMENTATION_BRIEF.md` →
`14_OPUS_REVIEW_CHARTER.md`.

## 0. Re-validation (implementation branch)

_Recorded 2026-07-19 by the Claude Sonnet 5 implementation-writer session._

- Gate 1 owner acceptance: recorded (`12_…ADDENDUM.md` §I) — Pete approved
  the round-2 package directly, ratifying board 1 and recording an
  owner-authorized exception to the parallel manager sign-off. Product
  implementation is authorized.
- Design-gate merge: Azure PR 90 squash-merged
  `81a48c0df180e3dc27b4635e17bb16f25273f6fd` into `main` at merge commit
  `6d5ef46ce05bd7c3a3f6e4b4c356bdf9c9bc6fcd`; governance/docs only, no
  product file changed.
- Implementation branch: `work/2026-07-19-interview-public-gate-001`,
  created from that exact merge commit as base SHA.
- Reserved-file drift check: `git log 229bfba4…3fabb396..HEAD -- templates/interview_studio.html static/css/interview-studio.css static/js/interview-studio.js tests/test_interview_studio.py app.py`
  returns no commits — none of the four reserved files or `app.py` changed
  since this architecture was written. No re-plan required; proceeding per
  §1–§13 as written.

_Correction-round re-validation (2026-07-19, after the Codex Conditional
implementation review):_ `origin/main` advanced to
`8da639fd47df5af7c1a146fb8ccb8992805bd7a5` (Capture Media planning, Projects
direction, Bible v2.6 / Roadmap v2.5 authority documents, updated guardrail
suites) and was merged into the implementation branch; no overlap with this
package's reserved files. Bible v2.6 and Roadmap v2.5 were re-checked for
Interview Studio language: the public gate remains an authorized focused
public-surface refinement with no new constraints affecting this
architecture. The Codex review's three functional corrections (STAR renderer
classes, `aria-current="step"` stage semantics, truthful Interview AI
answer-basis label) are implementation-level fixes within §5.4, §2.3, and
§5.5 as specified — no architecture change was required to close them.

## 1. Authority manifest

| Authority | Identity | Role |
|---|---|---|
| Image 5 source | `C:\Users\peter\iCloudDrive\Documents\Career\Website\Changes\Interview Studio\ChatGPT Image Jul 19, 2026, 12_09_58 PM (5).png`; 1,990,578 bytes; 1536×1024; SHA-256 `7A03EE1F4569478F067EE2996C575B130077633CB6C2AAA36A058EFE772467DD` | Concept A controls default/light; Concept C controls optional dark |
| PUBLIC-01/02 board 1 | `artifacts/ps-interview-public-gate-001/gate-24-final-visual-review/PUBLIC-01-02-supplied-board-1.png`; SHA-256 `31488D93AE50ADBC959EBA948BB4F5E8FD331DAF0DA80CF0E633BFDB94BDEBB5` | **Recommended controlling authority for PUBLIC-01 and PUBLIC-02** (see 1.1) |
| PUBLIC-01/02 board 2 | `...supplied-board-2.png`; SHA-256 `6E9146AE133AC67A24ABD5373F95BCFF25D41A3A030717AD60CB30E11A755209` | Retained as decision history, not authority |
| PUBLIC-03…V02 final system | `...PeerSlate_Interview_Studio_PUBLIC-03-V02_Final_Visual_System.zip`; 13,786,088 bytes; SHA-256 `C4A0156AE572956AE0F7D99F0CCCFC483CB4B5D988207844F66FDDE0118F5599`; 28 exports + static source (per-member hashes in `ASSET_INDEX.md`) | Controls the seven PUBLIC-03…V02 states in both themes |
| Codex Gate 2.4 review | `08_GATE_24_FINAL_VISUAL_REVIEW.md` on this branch | Conditional review this architecture closes |

### 1.1 PUBLIC-01/02 controlling-board recommendation

The final ZIP states its system is controlled by the approved PUBLIC-01/02
system without naming a hash. Recommendation: **board 1
(`31488D93…DEBB5`) controls**, because it is the only board that matches the
binding composition in `09_DUAL_THEME_VISUAL_AUTHORITY_AND_CLAUDE_BRIEF.md`:

- one dominant `Start Interview Me` action, with **three quieter choices —
  Interview AI, Video Practice, History** (board 2 renders three co-equal
  "Start →" cards, duplicates Interview Me as a card, and drops History from
  the card row);
- separate PUBLIC-01 and PUBLIC-02 mobile columns per theme (board 2 merges
  them into one combined mobile column per theme);
- the persistent four-item truth strip plus the
  "No sign-in. No account. No cloud history." / "Coaching happens after
  submission." baseline row.

Board 1 panel identification (all eight panels are individually labeled in the
image; percentages of the 1536×1024 canvas, left→right, top→bottom):
row 1 (y ≈ 0–55%): PUBLIC-01 desktop light, PUBLIC-01 desktop dark,
PUBLIC-02 desktop light, PUBLIC-02 desktop dark (each ≈ 25% wide);
row 2 (y ≈ 55–100%): PUBLIC-01 mobile light, PUBLIC-01 mobile dark,
PUBLIC-02 mobile light, PUBLIC-02 mobile dark. The labeled panels are the
four-plus-four "separate primary exports" for PUBLIC-01/02; no derivative
crop files are generated so that the Pete-approved original remains the only
authority artifact. **Owner action: Pete ratifies board 1 as controlling with
one yes/no** (recorded in the addendum blockers).

### 1.2 Shared shell resolution (closes Codex correction 2)

The boards show the production truth: the existing site global header and
footer stay, and everything Studio-specific lives in a **Studio-local shell**
beneath the global header. The ZIP source's merged "PeerSlate | Interview
Studio" chrome is a renderer simplification, not a production instruction.

Production shell contract:

- `templates/base.html` global header, theme toggle, skip link, and footer are
  untouched (read-only files).
- Inside `.is`, a Studio bar renders: "Interview Studio" identity (gold serif
  wordmark treatment per mockups), the four-item mode row (Interview Me,
  Interview AI, Video Practice, History), and the compact demo-profile chip
  ("PUBLIC DEMO PROFILE / Pete Carter"). This replaces the current oversized
  `is__hero` + `is__navigation` pair.
- The mockup footer line "Design authority · no production behavior" is
  mockup-only and must never ship. The line "Public Interview Studio ·
  browser-local practice" ships as a small Studio-scoped baseline inside `.is`.

## 2. One product, one DOM, one state machine

Routes, APIs, entitlements, storage, and endpoints are unchanged:
`/interview-studio`, `/interview-studio/history`, legacy redirects,
`POST /api/interview/review|improve|model-answer`, storage namespace
`peerslate:interview-studio:<profile>:v1:*`, entitlement data attributes.
`app.py` is not edited.

### 2.1 Views and the new orientation view

| View | Entry | Server-rendered initial? | Notes |
|---|---|---|---|
| `orientation` (**new**) | `GET /interview-studio` with **no** `mode` query param and not `/history` | Yes | PUBLIC-01 composition; dominant Start Interview Me |
| `practice` (me) | `?mode=me`, or client transition from orientation | Yes | PUBLIC-02/03/04/V01 |
| `ai` | `?mode=ai` | Yes | PUBLIC-05 |
| `video` | `?mode=video` | Yes | PUBLIC-06/V02 |
| `history` | `/interview-studio/history` | Yes | PUBLIC-07 |

Feasibility constraint honored: `app.py` currently passes
`interview_initial_view`/`interview_initial_mode` and cannot be edited. The
orientation view is derived **template-only**:
`{% set is_orientation = interview_initial_view != 'history' and not request.args.get('mode') %}`.
When true, the orientation panel is server-rendered visible and the practice
panel is present but `hidden` (all existing `data-is-*` hooks remain in the
DOM, so existing server-render tests and the no-JS truth requirement hold).
Orientation actions are real links (`?mode=me`, `?mode=ai`, `?mode=video`,
`/interview-studio/history`) so they work without JavaScript; with JavaScript
they are intercepted into the existing `setMode(..., true)`/pushState flow.
`popstate` handling gains the no-param → orientation case.

### 2.2 State machine (per view)

Existing machine and hooks are preserved; states are re-skinned, not rebuilt.

- practice: `drafting` (PUBLIC-02) → `processing` (PUBLIC-03; answer readOnly,
  `aria-busy`, preserved) → `review` (PUBLIC-04) → optional `improve`
  (compare/editable draft) → `drafting` of next question; failure branch
  `error` (PUBLIC-V01) with Keep editing / Retry coaching.
- ai: `idle` → `loading` → `result` (best-practice | public-profile | compare)
  → `error`; follow-up gated on server context token (unchanged).
- video: `idle` (camera off) → `requesting` → `live` → `recording` (3-min cap)
  → `playback` → `discarded`; `denied/unavailable` (PUBLIC-V02); typed
  transcript continuation into the shared review path (unchanged behavior).
- history: `list` ↔ `detail` (dialog, `?session=` deep link) with `empty` and
  `storage-unavailable` states; filters; goal; clear-local.
- Theme switch is **not** a state: no Studio code observes it (§6).

### 2.3 Per-question stage rail (replaces the percent bar)

PUBLIC-02/03/04/V01 show a five-circle rail plus "Question N of M". The rail
is the **current question's flow**, not the question count:

| Stage | drafting | processing | review | improve open | after advance |
|---|---|---|---|---|---|
| 1 Draft | current | done | done | done | reset to current |
| 2 Coaching request | — | current (V01 failure keeps 2 current with error present) | done | done | — |
| 3 Review | — | — | current | done | — |
| 4 Improve | — | — | — | current | — |
| 5 Continue | — | — | — | — | — |

DOM: `<ol class="is__stages" data-is-stage-rail aria-label="Answer progress">`
with five `<li>` (`is-done`/`is-current` classes, `aria-current="step"` on the
current one, visually hidden stage names). "Question N of M"
(`data-is-question-position`) remains the session-position text driven by the
real queue length (1, 5, or 10 — never hardcode 5 questions). **All five
stage circles render at every viewport** — the mockup's mobile
`nth-child(n+5){display:none}` defect is corrected by tightening circle size
and connector length at ≤48rem (28px circles per the mockup's own mobile
spec, wrapping to a second row only if width forces it). The old
`<progress>` bar and percent readout are retired in practice view; video view
keeps its compact "Question N of M · Local rehearsal" text header per
PUBLIC-06.

## 3. Semantic token architecture

One token layer on `.is`, consumed by every component; dark overrides **only
token values** under `body[data-theme="dark"] .is`. No component may hardcode
a theme color. Fonts: mockup `NotoSerif`/`InterDisplay` are renderer stand-ins
— production uses the brand pair already loaded on the page: Newsreader
(`--ps-font-display`) for serif/editorial, Inter (`--ps-font-ui`) for UI.

### 3.1 Token sheet with measured WCAG contrast

Light values come from the approved mockup source (`source/styles.css`
`body.light`), with three measured corrections (marked ▲) required by WCAG AA
and already anticipated by the Codex review. Ratios were computed with the
WCAG relative-luminance formula.

| Token | Light | Dark | Use / measured contrast |
|---|---|---|---|
| `--is-canvas` | `#fbf8f2` | `#03101d` | page wash behind `.is` |
| `--is-canvas-2` | `#fffdfa` | `#071a2b` | header/bar wash |
| `--is-surface` | `#fffefa` | `#091827` | cards, dialogs |
| `--is-surface-2` | `#f7f1e7` | `#0c2235` | recessed wells, banners |
| `--is-ink` | `#0c2345` | `#f4efe6` | headings: 14.76–15.51 light; 14.15–16.73 dark — AA/AAA |
| `--is-text` | `#283b58` | `#d7dde6` | body: 10.07–11.21 light; 11.86–14.03 dark — AA/AAA |
| `--is-text-muted` | `#60708a` | `#9facbd` | meta: 4.74–4.98 light; 7.03–8.31 dark — AA |
| `--is-gold-text` ▲ | `#8A5A00` (mockup `#b87900` measures 3.43–3.60 and fails normal-text AA) | `#d99a2b` (7.35–7.86) | eyebrows, gold text, source labels: 4.92–5.87 light — AA |
| `--is-gold` | `#B87900` | `#d99a2b` | meaningful gold borders/indicators (light 3.43–3.60 ≥ 3:1 non-text) |
| `--is-gold-bright` | `#d2a24b` | `#f1bd5c` | **decorative only in light** (2.20–2.31 < 3:1): truth-strip base accent, fills behind dark ink; in dark it is a text-capable accent (10.39–11.11) |
| `--is-gold-soft` | `#f6e9c9` | `rgba(217,154,43,.12)` | soft gold fills |
| `--is-line` | `#d9d1c4` | `rgba(207,159,70,.26)` | decorative separators only (≈1.5 / ≈2.68 — never the sole boundary of a control) |
| `--is-line-strong` | `#c9bca9` | `rgba(207,159,70,.42)` | card edges paired with surface/shadow contrast |
| `--is-action-primary` / `-strong` | `#0d356d` / `#092954` | `#f4bd58` / `#d79220` | primary button gradient; label `#fff` on light (12.02–14.42), `#101722` on dark (6.87–10.51) |
| `--is-action-primary-text` | `#ffffff` | `#101722` | |
| `--is-focus` | `#0b2f62` (12.40–13.03) | `#f1bd5c` (10.39–11.11) | 3px outline + 2–3px offset on every focusable |
| `--is-success` | `#1E725F` (5.74; 4.99 on soft) | `#54b696` (7.26) | success text/icons; **teal = success only** |
| `--is-success-soft` | `#e4f1ed` | `rgba(44,139,112,.16)` | |
| `--is-caution-text` ▲ | `#7a4d00` (7.20; 6.52 on soft — mockup `#a76600` measures 4.14 on `--is-caution-soft` and fails normal-text AA there) | `#e0a13a` | caution text on caution surfaces |
| `--is-caution-soft` | `#fff1d8` | `rgba(222,151,39,.15)` | amber notice bands |
| `--is-error` | `#b03434` (6.14; 5.29 on soft) | `#e45b5b` (5.08) | true error/destructive only |
| `--is-error-soft` | `#fbe9e7` | `rgba(202,57,57,.15)` | |
| `--is-shadow` | `0 16px 45px rgba(31,45,66,.10), 0 2px 8px rgba(31,45,66,.06)` | `0 24px 64px rgba(0,0,0,.35), inset 0 1px rgba(255,255,255,.02)` | measured paper depth / cinematic depth |
| `--is-overlay` | `rgba(10,27,54,.30)` | `rgba(0,0,0,.55)` | dialog backdrop |

▲ Third correction (dark step-done disc): white ✓ on `#54b696` measures 2.47.
Done-stage discs use fill `#1E725F`, border `#54b696`, glyph `#ffffff`
(5.79 glyph contrast; 7.26 border-vs-surface) in dark; light uses fill
`#1E725F`, glyph `#ffffff`.

Dark soft-band composites (soft fill alpha-blended over `--is-surface`,
worst case) all measured AA: caution text `#e0a13a` 6.35, error text
`#e45b5b` 4.60, success text `#54b696` 6.08, gold text `#d99a2b` 6.14.

Backgrounds: light `.is` canvas is the warm ivory wash (flat `--is-canvas`
with the mockup's faint vignette); dark is the layered stage
`radial-gradient(circle at 68% 18%, rgba(207,139,36,.10), transparent 28%),
radial-gradient(circle at 18% 78%, rgba(19,51,78,.38), transparent 40%),
linear-gradient(180deg,#020b14,#061522 45%,#03101d)`. The current
photo-image `is__backdrop` and the site sky remain removed/hidden. Never flat
pure black; never room-wide glow.

Prohibited: pink/rose/magenta/coral/purple accents; teal as active/current
accent; gold on the error/destructive palette; neon or gaming glow effects.

## 4. Component inventory (doc 09 names → production mapping)

| # | Component (09) | Production mapping | Key semantics |
|---|---|---|---|
| 1 | `StudioShell` | base.html global chrome (unchanged) + new `.is__bar` (identity + mode row + profile chip) + existing skip target, `[data-is-live]` polite region | mode row keeps the current model: 3 tabs (`role="tab"`, roving tabindex, arrow keys) + History link (`aria-current="page"` when active); visually the four items are styled identically per the boards |
| 2 | `StudioOrientation` | **new** `.is__panel[data-is-panel="orientation"]` server-rendered per §2.1 | eyebrow "REAL PRACTICE. REAL COACHING. REAL GROWTH.", serif headline, three support lines, dominant `Start Interview Me` (real link `?mode=me`), three quieter cards (Interview AI, Video Practice, History — real links), truth strip |
| 3 | `PublicDemoProfile` | chip in `.is__bar` + right-rail card on every view (avatar, serif "Pete Carter", role, "Public demo profile", rule, "◆ Grounded only in his approved public résumé. **You are not signed in as Pete.**") | server-rendered from existing `interview_profile` context; never implies session identity |
| 4 | `ModeChoice` | existing tabs/link + orientation cards | availability from existing entitlement attributes; disabled modes keep `aria-disabled` + explanation + fallback |
| 5 | `PracticeShell` | existing `[data-is-practice-stage]` re-skinned: "Interview Me Practice" label, stage rail (§2.3), serif question, muted guidance line (maps `data-is-intent` text), answer composer, dictation aid, Submit answer, session-setup disclosure (§5.2), Tips/Goal support | |
| 6 | `ProcessingState` | existing `[data-is-reviewing]` + `[data-is-submitted]` re-composed as PUBLIC-03: "YOUR SUBMITTED ANSWER · PRESERVED" card + processing banner + right-rail Coaching status card (`[data-is-coaching-status]`, new) | answer readOnly + `aria-busy`; live region announces submit/complete (existing messages) |
| 7 | `BottomLineReview` | existing `[data-is-feedback]` re-composed as PUBLIC-04 (§5.4) | score `role="img"` label "Overall interview score … practice signal, not an employer prediction" |
| 8 | `InterviewAIWorkspace` | existing panel re-composed as PUBLIC-05 (§5.5) | grounding modes stay a real `radiogroup` styled as the three selector cards |
| 9 | `VideoPracticeWorkspace` | existing panel re-composed as PUBLIC-06 (§5.6); rename "Video Me" → **"Video Practice"** everywhere user-visible | permission → live → record → playback sub-states; transcript continuation is a visible first-class control |
| 10 | `BrowserHistoryWorkspace` | existing history panel re-composed as PUBLIC-07 (§5.7) | filters/detail/goal/growth preserved via quiet controls + disclosures |
| 11 | `RecoveryPanel` | V01/V02 compositions (§5.8–5.9) on the existing error paths | error band receives focus (`tabindex="-1"`), live region announces (existing messages) |
| 12 | `DisclosureOrDialog` | native `<dialog>` (queue, settings, history detail — unchanged mechanics) + `<details>` disclosures (session setup, score detail, reference example) | `showModal` focus containment; close returns focus to invoker (browser-native + existing close handlers); Escape and backdrop click preserved |

New hooks introduced (additive; every existing `data-is-*` hook is retained):
`data-is-panel="orientation"`, `data-is-stage-rail`, `data-is-coaching-status`,
`data-is-demo-card`, `data-is-truth-strip`, `data-is-session-setup`,
`data-is-score-detail`, `data-is-storage-note`.

## 5. Screen-by-screen specification

Copy rules: every string below that is bold-quoted is required truth language
from `05_OWNER_APPROVED_DESIGN_SCOPE.md`/mockups and must appear server-rendered.
All screens keep the truth strip (§5.10) and demo-profile presence.

### 5.1 PUBLIC-01 Orientation (board 1)

Composition per §4 row 2. Support lines: "Answer questions in your own
words." / "Get coaching after you submit." / "Your practice stays in this
browser until you submit an answer for coaching." — the board's third line
("Everything you do stays in this browser.") is corrected because it is
literally false at submit time (deviation D20); the baseline row "No sign-in.
No account. No cloud history." / "Coaching happens after submission." renders
under the strip. Quieter cards use truth-corrected board copy (Interview AI:
"See a best-practice example, Pete's public-profile example, and a side-by-side
comparison — every answer labeled by source." — the board's "3 trusted
sources" misstates the three *views* as external sources, deviation D19;
Video Practice: "Rehearse on camera locally. Review your recording here.
Nothing is uploaded or analyzed."; History: "Your drafts, goals, attempts,
and completed practice—saved only in this browser."). Entitlement-disabled modes render the
card with `aria-disabled`, the reason, and the typed-practice fallback.
No-JS: all four actions are plain links; content fully server-rendered.
Mobile (board 1 row 2): single column — headline, dominant action, three
rows, collapsed "Truth & privacy" disclosure whose summary keeps the four
truths' short labels visible (labels may not disappear into the disclosure;
the disclosure only folds the long explanations).

### 5.2 PUBLIC-02 Active written practice (board 1)

- Header: "Interview Me Practice" section label; stage rail stage 1 current;
  "Question N of M"; "Est. time 15–20 min" chip only when M ≥ 5 (derived from
  real session format; never a fake constant).
- Serif question (`data-is-question`); guidance line "Write your answer in
  your own words." + autosave truth "**Your answer is saved in this
  browser.**" (maps the existing autosave meta; `data-is-autosave` becomes the
  save pill: "Draft ready" → "Saving…" → "✓ Draft saved in this browser" →
  storage-failure "Save failed — your text is still here").
- Composer: textarea (5,000 max, counter "0 words · 0 / 5,000 characters"),
  right rail "Answering aid" card: **Start dictation** (existing
  `data-is-mic="answer"`, visible mic error target under it), "Dictation is
  optional. You can speak and we'll transcribe into the box.", keyboard tips
  "Tab to navigate · Ctrl/Command + Enter to submit" (mockup's "Shift+Enter
  for line break" is replaced by the real shortcut — truth deviation D7).
- Transmission truth adjacent to the action: "**Questions and your answers are
  sent to PeerSlate only when you click Submit answer for coaching.**"
- Primary `Submit answer →`; baseline "Autosave: on · Last saved <time> ·
  Coaching happens after submission."
- Session setup (existing Experience/Question family/Session selects, Settings
  button, Up-next queue trigger) moves into a quiet
  `<details class="is__session-setup" data-is-session-setup>` labeled
  "Session setup · Experienced · Behavioral · 5-question mock" (summary shows
  live values; deviation D2 — the mockups omit these real controls and they
  may not be lost or promoted). New Question stays a quiet action beside the
  queue trigger. Tips (`data-is-tip`) and the reference example
  (`data-is-ai-reference`) render as quiet support under the composer.

### 5.3 PUBLIC-03 Processing, answer preserved

Per mockup: "YOUR SUBMITTED ANSWER · PRESERVED" card (`data-is-submitted`)
with character count and "Saved in this browser"; processing banner
(`data-is-reviewing`) "Preparing your coaching review — The submitted answer
remains visible while the full response is prepared." with Cancel retained
(existing behavior; quiet placement); right rail Coaching status card: serif
"Your answer is safe." + three rows (Answer received ✓ / Checking the question
rubric · current / Preparing bottom-line feedback) driven by request state:
row 1 done at submit, row 2 current while in flight, row 3 done only at
render (no fake progress timers — deviation-safe: the three rows reflect real
request lifecycle). Stage rail: 1 done, 2 current. Announcements: existing
("Coach review ready. Score …" on success).

### 5.4 PUBLIC-04 Bottom-line review

- Eyebrow "YOUR COACHING REVIEW"; serif "Bottom line first."; helper line.
- Bottom Line card: verdict + encouragement composed as the lead statement
  (`data-is-verdict`, `data-is-encouragement`); teal "✓ Added to this
  browser's practice history"; score ring right (`data-is-score-ring`,
  `role="img"`, ring stroke `--is-gold`, number `--is-ink`) with caption
  "**Practice signal — not an employer prediction**". Mobile: ring column
  narrows (78px) and the caption sets **below** the ring outside it — fixes
  the mockup's caption/ring overlap (correction, Codex item 4 of §D).
- "WHAT WORKED WELL" and "IMPROVE NEXT TIME" cards (`data-is-strengths`,
  `data-is-improvements`, gold bullets).
- "FRAMEWORK MAP · STAR" card (`data-is-star`): S/T/A/R tiles, letter disc
  semantic colors (done/good = success, warn = caution), status text
  "Situation · clear" style; each `li` keeps full sr text "Situation —
  Present: …reason".
- "Score detail" `<details data-is-score-detail>` containing the existing five
  dimensions list (`data-is-dimensions`) — real functionality preserved via
  disclosure (deviation D3).
- Right rail: "RECOMMENDED FOCUS" card rendered from real payload only:
  heading = first `improvements` item recast by existing content, body =
  `encouragement` (no invented analytics); demo profile card.
- Actions: `Try again` (existing retry), `Improve answer →` (existing improve
  entry), `Next question →` (existing advance — kept even though the mockup
  omits it; session flow requires it; deviation D4).
- Improve workspace: existing compare/editable-draft/`What changed`/Use This
  Draft/Retry Out Loud flow re-skinned with tokens; evidence suggestions
  ("Relevant history you may have missed", checkboxes) render inside the
  improve workspace entry area with their existing hooks and v1.2 copy
  (deviation D5: relocated from the feedback block; consulted, as today, when
  the improve request is sent). Stage rail: improve open → stage 4 current.

### 5.5 PUBLIC-05 Interview AI and compare

- Eyebrow "INTERVIEW AI"; serif "See the source. Compare the approach.";
  helper "Best-practice guidance, Pete's approved public-profile example, and
  side-by-side comparison remain clearly labeled."
- The three selector cards are the existing radiogroup (`data-is-ai-mode-group`)
  restyled: radios stay radios (`:has(input:focus-visible)` focus ring; gold
  selected border `--is-gold`); labels: "Best-practice example" / "**Use
  Pete's public history**" (adds the required "public"; deviation D6) /
  "Compare". Mode note strings keep their existing truthful variants.
- Question input + dictation + Get Answer: existing form re-skinned.
- Results keep existing semantics and labels: generic flag "Illustrative
  best-practice example — this is **not** Pete's real history."; grounded
  heading "Pete's answer" with source chip "Pete Carter · approved public
  résumé only"; "Why this answer works"; "Relevant history used" evidence
  chips; insufficient-evidence state unchanged.
- Compare mode presents the existing payload two-up per the mockup: left =
  Pete public-profile example (chip "Pete Carter · approved public résumé
  only"), right = best-practice comparison (chip "Best-practice example ·
  illustrative"), with "WHAT THE COMPARISON SHOWS" rendered from the real
  `bestPractice.whyItWorks` "Structural lessons" list. The mockup's
  Opening/Actions/Results judgment rows and meter bars are **not implemented**:
  no current endpoint produces that comparative analysis, and fabricating it
  violates the truth boundary (deviation D8; the mockup's "Your submitted
  answer" panel is banked as a future enhancement in §13). "Return to
  Interview Me →" renders as the existing practice-handoff action
  (`data-is-practice-answer` "Practice This Answer" keeps its behavior; label
  per mockup style).
- Right rail: "SOURCE BOUNDARIES" card — "Three views. No private history." +
  three bullets (best-practice is illustrative; Pete's example uses approved
  public résumé information only; compare shows differences without claiming
  an employer outcome); demo profile card. Follow-up form unchanged.
- Session setup in AI view: the disclosure stays available because
  Experience feeds the model-answer request today; the Session select keeps
  its existing AI-mode morph ("Answer basis: My History", disabled). The
  template's AI-grounding `fieldset` drops the colliding `is__mode` class
  (renamed `is__ai-grounding`) so the mode-row and grounding styles stop
  sharing a selector.

### 5.6 PUBLIC-06 Video Practice (local)

- Eyebrow "VIDEO PRACTICE · LOCAL ONLY"; serif "Rehearse on camera. Keep the
  recording here."; helper "Review your delivery locally. PeerSlate does not
  upload or analyze the recording."
- Camera stage sub-states on the existing machine: idle (empty state +
  `Enable Camera`), requesting (status line), live (preview + `Start Answer`),
  recording (red badge + timer + `Stop Recording`), playback ("● Local
  playback ready" pill + timer + native controls + `Delete local recording`
  (danger) + `Record again →` (primary)). Existing device-status line and
  errors retained.
- Right rail: "LOCAL REHEARSAL" card — playback state title ("Playback is
  ready." when applicable), "This recording stays in the current browser
  session and is never sent with your answer.", checklist (✓ Review the
  recording yourself / ✓ Record another take / ✓ Type or paste an answer for
  content coaching / ✗ No pace, eye-contact, filler-word, or confidence
  analysis); demo profile card.
- The typed continuation is a **visible control**, not a checklist mention
  (closes Codex §D PUBLIC-06 scope): the existing transcript composer
  ("Get content coaching from a transcript", textarea, dictation, Submit
  transcript) renders directly below the stage in every video sub-state.
- "**This preview uses your browser's local media APIs. The recording is not
  uploaded, analyzed, or retained by PeerSlate.**" stays. Rename ripple:
  every "Video Me" string (tab, announcements, history rows/detail, confirm
  prompts) becomes "Video Practice".
- Question context is retained in the video view (compact question block +
  "Question N of M · Local rehearsal") even though both PUBLIC-06 exports
  omit it: the rehearsal is an answer to a specific question, the recorder
  binds `media.question` into the browser history record, and New Question /
  transcript-coaching flows depend on it (deviation D21).

### 5.7 PUBLIC-07 Browser-local History

- Eyebrow "HISTORY · THIS BROWSER ONLY"; serif "Your practice history on this
  device."; helper "Drafts, goals, completed attempts, and coaching results
  are stored only in this browser."
- Amber notice band (always visible): "**No account or cloud history.**
  Clearing browser data, using another browser, or changing devices may
  remove or hide these records."
- "RECENT COMPLETED ATTEMPTS" card: existing session rows re-skinned (title,
  "Today · Interview Me · completed coaching" meta, gold score pill); rows
  open the existing detail dialog (deep link `?session=` preserved); the
  existing Mode/Competency/Time filters render as quiet selects in the card
  header (deviation D9 — mockup omits them; functionality preserved).
  Empty state: "No completed sessions yet …" with `Start practicing` link
  (existing), styled per system.
- "PRACTICE GOALS" card: real numeric goal only — target input + Save
  (existing hooks), teal progress bar with "**<avg>% average toward a
  <goal>% target**" from real records; "Recommended next session" row
  (existing recommendation + Practice this). The mockup's invented analytics
  ("4 of 6 recent answers included a measurable result") are **not
  implemented** — not computable from stored records (deviation D10). The
  derived focus line uses the existing lowest-dimension statistic
  ("Focus: strengthen <dimension>") only when ≥2 scored attempts exist.
- "Practice detail" disclosure: summary stats (questions answered, average,
  strongest competency) + growth bars (existing) fold here to keep the
  composition calm (deviation D11).
- Clear row: "Deletes local Studio records from this browser." +
  `Clear local history` (danger outline; existing confirm + reset behavior).
- Right rail: "LOCAL STORAGE" card — "Your history does not follow you." +
  "There is no account-backed history or cross-device synchronization in the
  current public Studio."; demo profile card.
- Storage-unavailable state (`data-is-storage-note`): when `localStorage`
  probes fail, a caution band renders: "This browser is blocking local
  storage. Practice still works, but drafts, history, and goals cannot be
  saved on this device." — driven by the existing try/catch helpers (a probe
  on init; no new storage semantics). History disclosure line (existing) is
  retained under the cards.

### 5.8 PUBLIC-V01 Processing failure

Existing error path re-composed: error band (`data-is-review-error`,
`tabindex="-1"`, focused on failure) "**Coaching could not be completed.**
Your answer is still here. Edit it or retry the coaching request without
re-entering your work."; answer card retitled "YOUR ANSWER · PRESERVED AND
EDITABLE" (textarea editable again); actions `Keep editing` (focus textarea) +
`Retry coaching →` (resubmit current text — same submit path; disabled while
in flight so repeated failures stay calm); right rail "WHAT HAPPENED" card
("The coaching service did not return a usable review." / "No score or
partial feedback has been created. Your browser-local draft remains
available."). Stage rail: 1 done, 2 current + error present. Live region:
existing "The review could not be completed. Your answer is safe."

### 5.9 PUBLIC-V02 Camera/microphone denied

Existing denial path re-composed: eyebrow "VIDEO PRACTICE · PERMISSION
DENIED"; serif "Camera or microphone access is unavailable."; helper "You can
retry permission later or complete the same interview question through
written practice now."; caution band "Browser permission was not granted. No
camera or microphone media was captured, uploaded, or analyzed."; dashed
stage panel "Continue without camera or microphone." + "Typed practice
remains fully available. Optional dictation is unavailable until microphone
permission is restored."; "WRITTEN FALLBACK" = the transcript composer
promoted as the dominant object with `Continue with written answer →`
(existing transcript-submit path into shared coaching); right rail "TRY
CAMERA AGAIN LATER" card (three real remediation bullets + `Retry permission`
→ existing device-settings/enable path, announcing the result). Denial copy
comes from the existing `friendlyMediaError` map (which distinguishes denied /
not-found / in-use — richer than the mockup's single string; kept).

### 5.10 Truth strip (all views)

`<ul class="is__truth" data-is-truth-strip>` — four items, gold ring icons,
gold baseline accent (decorative `--is-gold-bright`), server-rendered:

1. "Questions and your answers are sent to PeerSlate only when you submit for
   coaching."
2. "Drafts, goals, attempts, and History are saved only in this browser."
3. "Video Practice remains local. Media is not uploaded or analyzed."
4. "Scores are practice signals, not employer predictions."

Desktop 4-across; ≤48rem stacked rows. Never hidden by any state, dialog, or
disclosure.

## 6. Theme mechanism and no-state-loss proof

Mechanism: the existing global theme controller only —
`static/js/theme-toggle.js` flips `body[data-theme]` between `modern-blue`
and `dark` and persists `ps-theme`; the base anti-flash script applies the
stored preference before paint; no-JS loads light. The header exposes the
primary switch. Each native modal dialog also exposes a synchronized switch
proxy inside the modal because `showModal()` correctly makes the header
inert. Those proxies invoke the same global controller and add no theme
logic to the Studio script (D22).

Architecture invariants (each is reviewable in the diff and guarded by tests):

1. `static/js/interview-studio.js` contains no reference to `ps-theme`,
   `data-theme`, `theme-toggle`, or `matchMedia('(prefers-color-scheme'` —
   the Studio never observes or reacts to theme (guardrail test asserts the
   strings' absence; the existing `prefers-reduced-motion` matchMedia is the
   only allowed media query in JS).
2. All theming is CSS custom-property value swapping under
   `body[data-theme="dark"] .is { --is-…: …; }` plus a bounded list of
   dark-only decorative rules (backdrop gradient, shadow tuning). Theme
   selectors may adjust color, background, border-color, shadow, filter,
   outline-color — never `display`, `visibility`, `content`, position,
   or size of stateful elements, so geometry, focus, caret, selection, scroll,
   dialogs, and media playback are untouched by construction.
3. No `innerHTML` replacement, re-render, or script re-init occurs on theme
   change (nothing listens for it). The mockup renderer's query-string theme
   + `document.body.innerHTML` repaint is explicitly **not** the production
   architecture (Codex correction 11).
4. If storage is unavailable, the global toggle already degrades to
   page-view-only theming; Studio storage helpers already no-op safely.
   Neither claims persistence it did not achieve.

Manual proof matrix (implementation evidence; toggle theme mid-state, both
directions, desktop + 390px):

| # | State at toggle | Must survive unchanged |
|---|---|---|
| 1 | Orientation | scroll position, focused card |
| 2 | Drafting with unsaved text | textarea value, caret/selection, word count, save pill |
| 3 | Coaching request in flight | request completes and renders; submitted card intact |
| 4 | Review rendered | full review content, score ring value, disclosure open state |
| 5 | Improve open with edited draft | edited draft text, checked evidence boxes |
| 6 | AI result + typed follow-up | result, follow-up input value |
| 7 | Recording in progress | stream, timer, recording continues |
| 8 | Playback ready | blob URL playback still plays, elapsed position |
| 9 | History with filters + open detail dialog | filter values, dialog open, focused modal theme control |
| 10 | V01 error / V02 denied | error band, preserved answer, focus position |

## 7. Accessibility architecture

- **Focus**: visible 3px `--is-focus` outline, offset 2–3px, on every
  focusable (light navy 12.4:1; dark gold 10.4:1). Focus order follows DOM
  reading order per §5 compositions. Dialogs: native `showModal` containment;
  close restores invoker focus (existing handlers). Error transitions move
  focus to the error band (V01/V02, mic errors keep inline visible text).
  Mode changes announce via the single polite live region (existing
  `announce()` messages are retained verbatim except the Video Practice
  rename; new announcements are limited to storage-note appearance and the
  Retry-permission result, each announced once; dialogs and status cards do
  not add duplicate announcements).
- **Names/roles/states**: tabs (3) + history link per §4.1; stage rail `ol`
  + `aria-current="step"` + sr stage names; score ring `role="img"` with the
  practice-signal label; STAR items carry status in text, not color alone;
  radiogroup for AI grounding; disclosures are native `details/summary`;
  every icon is `aria-hidden` with adjacent text.
- **Reduced motion**: the existing kill-switch block stays (transitions/
  animations → 0.01ms, auto scroll behavior). Spinners stop; their meaning is
  carried by the always-present processing text. The dark gold focal
  treatment is static (no pulse/glow animation at any time). No state or
  meaning depends on motion.
- **Zoom/reflow 200%**: rem-based sizing throughout; existing breakpoints
  double as reflow at zoom (1280×720 @200% ≈ 40rem viewport → single-column
  layouts); no fixed heights on text containers; `min-height` decorative
  panels use `svh` caps for landscape (video stage `min(450px, 70svh)`).
- **Touch targets**: primary/secondary buttons ≥ 44px (mockup 54/50px);
  `small-btn`-equivalents and icon buttons raised to ≥ 2.75rem (44px)
  (deviation D12); dense meta links keep 44px hit areas via padding.
- **High contrast / forced colors**: extend the existing `prefers-contrast`
  and `forced-colors` blocks to the new components (stage rail discs get
  borders, ring gets `border: 3px solid Highlight`, truth strip borders
  `CanvasText`, backdrop removed).
- **Language**: copy guardrails from `02_EXPERIENCE_ACCESSIBILITY.md`
  (no "your private history", "account", "synced", "secure recording";
  dictation is not Capture).

## 8. Failure and unavailable-state matrix

| Condition | Behavior (all existing paths, re-skinned) | Visible truth |
|---|---|---|
| JavaScript unavailable | Server-rendered orientation/practice/ai/video/history content + real links; `<noscript>` note: "Interactive practice needs JavaScript. Everything shown here stays truthful: nothing is stored or sent by this page until you submit." | full truth strip + labels server-side |
| localStorage unavailable | init probe → §5.7 caution band; save pill failure copy; theme still switches for the page view | no false "saved" claims |
| Speech recognition unavailable/denied | existing visible mic error + typing continues | "You can keep typing." |
| Camera/mic denied or absent | PUBLIC-V02 composition; distinct copy per `friendlyMediaError` | "No camera or microphone media was captured, uploaded, or analyzed." |
| MediaRecorder unsupported | preview allowed, recording disabled + visible note (existing) | no fake recording |
| Coaching request fails | PUBLIC-V01; answer preserved + editable; Retry coaching | "No score or partial feedback has been created." |
| Improve request fails | existing failure copy; original answer unchanged | |
| AI request fails | existing error + previous result retained when present | |
| Repeated failures | error band persists; retry stays enabled after each settled attempt; no lockout, no fabricated partial success | |

## 9. File-by-file implementation mapping

The original implementation reservation covered the four product files.
The acceptance correction adds two narrowly bounded shared-file edits under
Pete's explicit 2026-07-20 owner authorization: the existing global theme
controller binds synchronized modal proxies, and `templates/base.html`
bumps that script's cache key. `app.py`, routes, APIs, global theme tokens,
and deployment configuration remain untouched.

### 9.1 `templates/interview_studio.html`

1. Replace hero + navigation with the Studio bar (§4.1) + orientation panel
   (§5.1, `request.args`-derived per §2.1).
2. Practice panel: stage rail, question header, composer + answering aid,
   session-setup disclosure, PUBLIC-03/04/V01 blocks, relocated evidence
   suggestions, score-detail disclosure, recommended-focus rail card.
3. AI panel: selector cards, result/compare re-composition, source-boundaries
   rail card.
4. Video panel: eyebrow header, stage sub-states, rehearsal rail card,
   visible transcript composer, V02 block.
5. History panel: notice band, three cards + disclosures, storage note,
   rail cards.
6. Truth strip include on all views; demo-profile chip + rail cards from
   existing `interview_profile` context.
7. Copy renames ("Video Practice", "Use Pete's public history",
   "Public demo profile" labeling; remove "Preparing as …" phrasing).
8. Bump asset versions: `css/interview-studio.css?v=studio-5a5c-1`,
   `js/interview-studio.js?v=studio-5a5c-1`.

### 9.2 `static/css/interview-studio.css`

Rewrite organized as: (1) token layer (§3, light values); (2) shell/bar;
(3) shared primitives (cards, buttons, pills, bands, truth strip, stage rail,
rail cards, dialogs); (4) view compositions; (5) responsive blocks (keep the
proven 72/56/48/36/32rem ladder; port the mockup's ≤700px decisions; all five
stage circles always visible); (6) a11y blocks (`prefers-reduced-motion`,
`prefers-contrast`, `forced-colors` extended); (7) single dark block:
`body[data-theme="dark"] .is { …token overrides… }` + bounded decorative
dark rules. Delete: photo backdrop, Foundation-C indigo/azure values, purple
family chip, and the entire PS-THEME-002 legacy dark block. Keep:
`.is [hidden]{display:none!important}`, sr-only utilities, focus-visible
discipline, `body.interview-studio-page .site-sky{display:none}`.

### 9.3 `static/js/interview-studio.js`

Bounded deltas (no fetch/endpoint/storage-schema changes):

1. `view` gains `orientation`; orientation links intercepted into
   `setMode(mode, true)`; popstate handles the no-param case; entering any
   mode hides the orientation panel.
2. Stage-rail renderer (`setStage(n)`) called from the existing transitions
   (drafting/reset=1, submit=2, render review=3, improve open=4, advance
   resets); removes percent readouts for practice view; session-setup
   disclosure summary text reflects the live level/family/format values.
3. Review render: verdict/encouragement into the bottom-line composition;
   recommended-focus card fill; score ring value + label (existing); "Added
   to this browser's practice history" line toggling with the real record
   write result.
4. V01 flow: on failure, retitle answer card state, focus the error band;
   `Retry coaching` resubmits current text; `Keep editing` focuses textarea.
5. Video: sub-state class toggles for the new compositions; playback pill +
   timer text; V02 composition toggle on denial; `Retry permission` wires to
   the existing enable path; rename announcements/labels to Video Practice.
6. History: storage probe → storage note toggle; card re-composition render
   targets; filters/goal/growth/detail unchanged logic.
7. Save pill states incl. storage-failure copy (existing writeJSON result).
8. String renames (Video Practice; mode announcements unchanged otherwise).
9. Delete nothing else; every existing listener, guard, abort controller,
   confirm, and announcement stays.

### 9.4 `tests/test_interview_studio.py`

Update assertions that pin replaced copy/structure; add focused coverage:

- Update: profile label test ("Preparing as" → demo-profile labeling:
  "Public demo profile", "You are not signed in as Pete."); "Video Me" →
  "Video Practice" strings; hero/mode markup selectors as re-composed;
  CSS-contract test additions (see below).
- Add: orientation server-render (no `mode` param → orientation visible,
  practice panel present but hidden; `?mode=me` unchanged); all four
  orientation links present without JS; truth strip four items on `/`,
  `?mode=video`, and `/history`; stage rail markup with five `li`;
  "Use Pete's public history" label; "Practice signal — not an employer
  prediction" adjacency to the score ring; V01/V02 required copy present in
  template; storage-note hook present.
- Theme guardrails: JS text contains none of `ps-theme` / `data-theme` /
  `theme-toggle`; CSS contains `body[data-theme="dark"] .is` exactly once as
  the dark token block anchor; CSS does not contain the retired photo
  backdrop path or `nth-child(n+5)` step hiding; CSS contains `#8A5A00`
  (light text-gold) and does not use `#b87900` as a `color:` value in the
  light token block (regex on the token layer).
- Keep every existing route/entitlement/API guard test green and unchanged
  unless its pinned copy moved (each such edit is enumerated in the
  implementation report).

Focused commands (from `03_VALIDATION_PLAN.md`): `tests/test_interview_studio.py`,
`tests/test_navigation.py`, `tests/test_site_rules.py`,
`tests/test_governance_pointers.py`, then the complete configured suite in the
repository venv.

## 10. Risk and feasibility matrix

| # | Risk | Severity | Mitigation | Verdict |
|---|---|---|---|---|
| 1 | Light gold text fails AA (mockup value) | High (was Codex item 4) | `--is-gold-text` `#8A5A00` measured 4.92–5.87 | Closed by §3 |
| 2 | Light `#d2a24b` used as meaningful boundary (< 3:1) | Medium | decorative-only rule; meaningful indicators use `--is-gold`/navy | Closed by §3 |
| 3 | Dark step-done glyph 2.47:1 | Medium | disc `#1E725F` + border `#54b696` + white glyph | Closed by §3 |
| 4 | Theme switch state loss | High | zero theme code in Studio JS; CSS-value-only theming; guardrail tests + §6 matrix | Closed by design; proven at implementation |
| 5 | Orientation view without `app.py` | High if misread | template `request.args` derivation §2.1; server-rendered; tests | Feasible |
| 6 | Mockup implies non-existent compare analytics | High (truth) | D8: real payload only; banked future enhancement | Closed |
| 7 | Mockup implies non-computable history analytics | Medium (truth) | D10: real stats only | Closed |
| 8 | Real controls missing from mockups (selects/queue/settings/filters/goal) | High (functionality) | D2/D9/D11 disclosures; nothing removed | Closed |
| 9 | Test-suite copy pinning breaks | Medium | §9.4 enumerated updates; run focused suite first | Managed |
| 10 | `backdrop-filter` cost on low-end devices | Low | dark theme uses opaque layered surfaces (no blur required); light keeps blur only on the bar | Managed |
| 11 | Forced-colors/high-contrast regressions on new components | Medium | §7 extensions + implementation screenshots | Managed |
| 12 | Long content overflow (question/answer/feedback/history) | Medium | wrap rules, no nowrap on user content except rows with detail dialogs; long-content evidence required | Managed |
| 13 | Landscape 844×390 clipping | Medium | svh caps, no fixed stage heights | Managed |
| 14 | Font swap layout shift | Low | Newsreader already preloaded on the page today | Managed |

Feasibility verdict for implementation inside the four reserved files, with
no API/route/schema change and no unreserved file: **Pass** (the overall gate
readiness result, which also weighs design-package evidence gaps, is recorded
in the addendum as Conditional).

## 11. Deviation register (mockup → production)

Every deviation improves truth, accessibility, or real-product fit per
`OWNER_VISUAL_INTEGRITY_STANDARD.md`; none dilutes the approved composition.
Manager/Pete acceptance of this register is part of gate approval.

Design-level 5A/5C parity statement (verified in this session across all 28
ZIP exports and both boards): every state pairs light and dark with identical
content order, components, controls, labels, and responsive structure;
themes differ only in token values and decorative depth treatments. The
implementation-time parity matrix (§12) proves the same property for the
built product.

| # | Deviation | Class |
|---|---|---|
| D1 | Global site header/footer retained; ZIP's merged chrome treated as renderer simplification (per boards) | shell truth |
| D2 | Experience/Family/Session selects, Settings, queue, New Question preserved in a quiet session-setup disclosure (mockups omit them) | functionality preservation |
| D3 | Five scoring dimensions preserved under "Score detail" disclosure | functionality preservation |
| D4 | `Next question →` action retained on review | functionality preservation |
| D5 | Evidence suggestions relocated into the improve workspace with existing v1.2 copy | composition mapping |
| D6 | AI grounding label "Use Pete's public history" (boundary contract wording; mockup: "Pete public-profile example" stays on the result chip) | truth |
| D7 | Keyboard tip states the real shortcut (Ctrl/Command + Enter) instead of mockup's Shift+Enter line | truth |
| D8 | Compare renders real payload (Pete example + best-practice + structural lessons); no fabricated Opening/Actions/Results judgments or meters; visitor-answer panel banked | truth |
| D9 | History filters retained in card header | functionality preservation |
| D10 | History "Practice goals" shows only computable stats (target progress, lowest-dimension focus) | truth |
| D11 | Summary/growth stats fold into "Practice detail" disclosure | composition mapping |
| D12 | Compact controls raised to ≥44px targets (mockup 42px small buttons) | accessibility |
| D13 | Light text-gold `#8A5A00`; `#d2a24b` decorative-only; dark done-disc recolor | accessibility (measured) |
| D14 | All five stage circles visible on mobile (mockup hides the fifth) | correction of authority defect |
| D15 | Score-ring caption placed below the ring on mobile (mockup overlaps) | correction of authority defect |
| D16 | Newsreader/Inter replace the renderer's NotoSerif/InterDisplay stand-ins | brand token |
| D17 | Mockup-only footer line "Design authority · no production behavior" not shipped | truth |
| D18 | Est-time chip only when derived from the real session format | truth |
| D19 | Orientation Interview AI card copy names the three labeled views instead of the board's "3 trusted sources" (no such external sources exist) | truth |
| D20 | Orientation support line "Your practice stays in this browser until you submit an answer for coaching." replaces "Everything you do stays in this browser." (false at submit time) | truth |
| D21 | Video view keeps a compact question block + "Question N of M · Local rehearsal" though PUBLIC-06 exports omit question context (recording is bound to a question; history records and flows depend on it) | functionality preservation |
| D22 | Each native modal includes a synchronized theme-switch proxy owned by the existing global theme controller; the header switch is inert while `showModal()` is open, so an in-modal proxy is required to satisfy the open-dialog no-state-loss contract | accessibility and functionality preservation |

## 12. Implementation evidence matrix (what the writer must return)

- 18 primary screenshots: PUBLIC-01…V02 × light/dark at 1440×900 (desktop) —
  named `IMPL-<screen>_<theme>_desktop.png`; plus 1920×1080 spot checks for
  PUBLIC-01/02/04.
- Mobile portrait 390×844 for all nine screens × both themes; mobile
  landscape 844×390 for written, review, video, history, failure; 200% zoom
  reflow for PUBLIC-02/04/07.
- Keyboard-focus walk (visible outlines) for orientation, practice, AI,
  video, history, dialogs; reduced-motion capture of PUBLIC-03; long-content
  states (question/answer/feedback/history row); no-JS render of `/`,
  `?mode=video`, `/history`; storage-unavailable state; V01/V02 live
  reproductions; theme no-state-loss matrix §6 (10 rows, both directions).
- Complete test outputs (focused + guardrails + full configured suite),
  `git diff --check`, reserved-file audit, and the §11 register with any new
  deviations added and justified.
- 5A/5C parity matrix: per screen × theme — silhouette, hierarchy, dominant
  action, typography, spacing, color semantics, density, states — with
  match/exceed/deviation notes against the exact authority hashes (§1).

## 13. Out of scope / future bank (unchanged authority)

Visitor-answer comparison panel in Compare (needs either a comparative
endpoint or a defined client-side juxtaposition decision); worked-example
tour; authenticated `/app/interview-studio`; homepage walkthrough convergence
(Gate 4 of doc 10, only after the real Studio is released and verified live);
any Voice/Capture/Moment/Placement/Story/resume surface.

**Status (2026-07-19): implementation of this architecture is complete on
`work/2026-07-19-interview-public-gate-001` and awaiting Pete +
designated-manager (Claude Co-Work) acceptance. Not merged, not deployed,
not live. The original "design only" closing line applied to the design-gate
phase and was superseded by the Gate 1 approval recorded in
`12_…ADDENDUM.md` §I.**
