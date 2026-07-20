# Implementation Evidence Index — PS-INTERVIEW-PUBLIC-GATE-001

_Captured 2026-07-19 (Codex correction round) from the implemented product
running on the local dev server, branch
`work/2026-07-19-interview-public-gate-001` after the STAR-renderer,
`aria-current="step"`, and answer-basis-label corrections. 73 screenshots.
Every row of the architecture §12 matrix maps below to named files or an
identified verification result. Nothing here is a design export._

## State-reproduction techniques (disclosed)

| State | Technique | Why it is honest |
|---|---|---|
| PUBLIC-03 processing | The real coaching request held pending via route interception | The UI is under a genuinely pending request; nothing is simulated |
| PUBLIC-04 review | Real `/api/interview/review` round trips (with the V01 retry control when the intermittent backend 502 occurred) | Real coaching content, real scores |
| PUBLIC-05 AI | Real `/api/interview/model-answer` round trips (default question) | Real payload rendering |
| PUBLIC-06 live camera | Chromium fake-device test pattern (`--use-fake-device-for-media-stream`) | Real `getUserMedia`/preview pipeline; only the sensor is synthetic |
| PUBLIC-07 populated | Records seeded into the real browser-local storage schema (`peerslate:interview-studio:petec:v1:*`) | Exactly what the browser holds after real practice; schema byte-compatible |
| PUBLIC-V01 failure | Real network failure (route abort) through the real client error path | Same client behavior as the intermittent real 502s observed live |
| PUBLIC-V02 denied | Permissions-empty browser context (no fake-media flags) → real `getUserMedia` rejection | Real denial/unavailable handling and copy |
| Storage unavailable | `localStorage` accessor made to throw before page scripts run | Real catch-path behavior in the app and theme scripts |
| No-JS | JavaScript-disabled browser context | Server-rendered truth only. Note: these three captures retain the sticky-header full-page stitching artifact because the style-neutralizing injection itself requires JS |
| 200% reflow | 720×450 CSS-pixel viewport (1440×900 at 200% equivalence) | Standard CSS-pixel zoom equivalence |

## Nine screens — primary implementation captures

| Screen | Desktop 1440 light / dark | Mobile 390 light / dark | Extra |
|---|---|---|---|
| PUBLIC-01 orientation | `IMPL-PUBLIC-01_ORIENTATION_LIGHT_DESKTOP` / `…_DARK_DESKTOP` | `…_LIGHT_MOBILE` / `…_DARK_MOBILE` | 1920×1080: `…_LIGHT_DESKTOP1920` |
| PUBLIC-02 active practice | `IMPL-PUBLIC-02_ACTIVE_PRACTICE_LIGHT_DESKTOP` / `…_DARK_DESKTOP` | `…_LIGHT_MOBILE` / `…_DARK_MOBILE` | 1920: `…_LIGHT_DESKTOP1920`; landscape + zoom below |
| PUBLIC-03 processing | `IMPL-PUBLIC-03_PROCESSING_LIGHT_DESKTOP` / `…_DARK_DESKTOP` | `…_LIGHT_MOBILE` / `…_DARK_MOBILE` | reduced-motion below |
| PUBLIC-04 review | `IMPL-PUBLIC-04_BOTTOM_LINE_LIGHT_DESKTOP` / `…_DARK_DESKTOP` | `…_LIGHT_MOBILE` / `…_DARK_MOBILE` | 1920: `…_LIGHT_DESKTOP1920`; landscape + zoom below; corrected STAR tiles visible |
| PUBLIC-05 Interview AI | `IMPL-PUBLIC-05_INTERVIEW_AI_LIGHT_DESKTOP` / `…_DARK_DESKTOP` | `…_LIGHT_MOBILE` / `…_DARK_MOBILE` | grounding-focus below |
| PUBLIC-06 Video Practice | idle: `IMPL-PUBLIC-06_VIDEO_IDLE_LIGHT_DESKTOP` / `…_DARK_DESKTOP`; live: `IMPL-PUBLIC-06_VIDEO_LIVE_LIGHT_DESKTOP` / `…_DARK_DESKTOP` | idle `…_LIGHT_MOBILE` / `…_DARK_MOBILE` | landscape below |
| PUBLIC-07 History | populated: `IMPL-PUBLIC-07_HISTORY_LIGHT_DESKTOP` / `…_DARK_DESKTOP`; empty: `IMPL-PUBLIC-07_HISTORY_EMPTY_LIGHT_DESKTOP` / `…_DARK_DESKTOP` | populated `…_LIGHT_MOBILE` / `…_DARK_MOBILE` | landscape + zoom + storage-unavailable below |
| PUBLIC-V01 failure/retry | `IMPL-PUBLIC-V01_FAILURE_RETRY_LIGHT_DESKTOP` / `…_DARK_DESKTOP` | `…_LIGHT_MOBILE` / `…_DARK_MOBILE` | landscape below |
| PUBLIC-V02 media denied | `IMPL-PUBLIC-V02_MEDIA_DENIED_LIGHT_DESKTOP` / `…_DARK_DESKTOP` | `…_LIGHT_MOBILE` / `…_DARK_MOBILE` | typed fallback: `IMPL-PUBLIC-V02_TYPED_FALLBACK_LIGHT_DESKTOP` |

## Architecture §12 requirement → evidence map

| Requirement | Evidence |
|---|---|
| 18 primary desktop screenshots (nine screens × both themes) | The Desktop 1440 column above — 20 including the two PUBLIC-06/07 sub-state pairs |
| 1920×1080 spot checks (PUBLIC-01/02/04) | `…_LIGHT_DESKTOP1920` ×3 |
| Mobile portrait 390×844, all nine screens × both themes | The Mobile column above (18 files) |
| Mobile landscape 844×390 — written, review, video, history, failure | `IMPL-PUBLIC-02_ACTIVE_PRACTICE_{LIGHT,DARK}_LANDSCAPE`, `IMPL-PUBLIC-04_BOTTOM_LINE_{LIGHT,DARK}_LANDSCAPE`, `IMPL-PUBLIC-06_VIDEO_IDLE_{LIGHT,DARK}_LANDSCAPE`, `IMPL-PUBLIC-07_HISTORY_{LIGHT,DARK}_LANDSCAPE`, `IMPL-PUBLIC-V01_FAILURE_RETRY_{LIGHT,DARK}_LANDSCAPE` (10) |
| 200% zoom reflow (PUBLIC-02/04/07) | `…_ZOOM200` ×6 (both themes) |
| Keyboard-focus walk | `IMPL-EVIDENCE-FOCUS_PUBLIC-02_{LIGHT,DARK}_DESKTOP` (answer textarea, visible 3px outline), `IMPL-EVIDENCE-FOCUS_PUBLIC-05_GROUNDING_LIGHT_DESKTOP` (radiogroup), `IMPL-EVIDENCE-FOCUS_QUEUE_DIALOG_LIGHT_DESKTOP` (dialog focus containment); plus scripted keyboard walks recorded in the completion report §F (orientation → Start Interview Me; History → Back → orientation tab reachability) |
| Reduced motion | `IMPL-EVIDENCE-REDUCEDMOTION_PUBLIC-03_LIGHT_DESKTOP` (context-level `reduced_motion=reduce`; processing meaning carried by text) |
| Long content | `IMPL-EVIDENCE-LONGCONTENT_PUBLIC-02_LIGHT_{DESKTOP,MOBILE}` (275-char wrapped question + ~4,990-char answer, no clipping or horizontal scroll) |
| JavaScript unavailable | `IMPL-EVIDENCE-NOJS_{ORIENTATION,VIDEO,HISTORY}_LIGHT_DESKTOP` — server-rendered truth labels, real links, `<noscript>` band |
| Local-storage unavailable | `IMPL-PUBLIC-07_STORAGE_UNAVAILABLE_{LIGHT,DARK}_DESKTOP` — caution band, no false save claims |
| Media unavailable / permission denied | `IMPL-PUBLIC-V02_MEDIA_DENIED_*` ×4 — real rejection in a permissions-empty context (headless no-device environment surfaces the could-not-start variant of the same `friendlyMediaError` path; the denied-permission copy variant is exercised by the pre-existing unit-tested error map) |
| Errors, retry, recovery | `IMPL-PUBLIC-V01_FAILURE_RETRY_*` ×6 (real network failure; Keep editing + Retry coaching visible; answer preserved and editable); recovery-to-success proven live via the Retry-coaching control during the PUBLIC-04 captures |
| Typed fallback | `IMPL-PUBLIC-V02_TYPED_FALLBACK_LIGHT_DESKTOP` + the transcript composer visible in every PUBLIC-06/V02 capture |
| Theme no-state-loss (§6 matrix, 10 rows, both directions) | Scripted live verification (completion report §F): orientation scroll (pre-existing sitewide ~20–60px drift, documented), draft text + word count, in-flight request, rendered review, edited improve-draft, AI result + follow-up input, active recording, playback blob, history filters + open dialog, V02 typed fallback — all preserved across real `#theme-toggle` toggles |
| Screen-reader announcements | Not provable by screenshot; covered by the unchanged `announce()` live-region mechanism, the focused unit tests on live-region markup, and flagged in the completion report as a remaining manual-AT pass |
| Contrast spot checks | Measured values recorded in architecture §3.1 and re-verified live for the corrected dark done-disc (5.79:1) and current-disc (9.79:1); light text-gold 4.92–5.87:1 |

## Correction-round deltas visible in this set

- PUBLIC-04 captures show the **corrected STAR framework tiles**
  (`is__star-item`/`is__star-letter`/`is__star-label`, semantic status
  colors, mockup vocabulary) replacing the run-together text Codex flagged.
- The stage rail carries `aria-current="step"` on exactly one item in every
  capture (server-rendered and after transitions — verified by scripted DOM
  checks in both themes, recorded in the completion report §F).
- The Interview AI expanded setup shows the truthful
  **"Approved public résumé history"** answer-basis label:
  `IMPL-PUBLIC-05_ANSWER_BASIS_SETUP_LIGHT_DESKTOP` (captured with the
  session-setup disclosure open in AI mode; the previous "My History" string
  no longer exists anywhere in the source).

## 2026-07-20 acceptance addendum

The independent Codex acceptance pass reproduced a gap in the original
theme no-state-loss claim: while a native modal was open, the global header
switch was correctly inert, and an attempted outside click closed the dialog
instead of changing theme. The accepted correction adds a synchronized
theme switch inside each of the Queue, Settings, and History-detail dialogs,
all owned by the existing global theme controller. A real in-app-browser
pass at 1440px and 390×844 verified both toggle directions, open-dialog
retention, focused-switch retention, draft-text retention, synchronized
`aria-checked`, zero horizontal overflow at 390px, and zero console errors.
