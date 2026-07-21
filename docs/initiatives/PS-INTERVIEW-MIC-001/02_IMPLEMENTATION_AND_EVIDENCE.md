# PS-INTERVIEW-MIC-001 — Implementation and evidence

_Branch `work/2026-07-20-interview-me-microphone-001`, base `origin/main` at
`ed3409a902f38e9437f6fbf70d3f2f61625037f4`._

Decision record: `01_ARCHITECTURE_DECISION.md` — option (a), browser-native
`SpeechRecognition`, extending the one existing `startDictation()` helper.

## What changed

| File | Change |
|---|---|
| `static/js/interview-studio.js` | Continuous dictation state machine replacing the single-utterance helper |
| `templates/interview_studio.html` | Control moved beside Submit answer; status/interim/truth elements; `aria-pressed`; asset signature `studio-5a5c-3` |
| `static/css/interview-studio.css` | Listening, unavailable, note, status, and interim-preview styling on existing theme tokens |
| `tests/test_interview_studio.py` | New `InterviewStudioDictationTests` (25 tests) + one updated assertion |

No server file changed. `app.py` was not touched, so the concurrent
`validate_interview_review` / `validate_interview_model_answer` lane is not
affected.

## Behaviour verified in a real browser

Driven against a running app at `127.0.0.1:5077` with a controllable
`SpeechRecognition` stub, so the real state machine executed. Microphone
permission cannot be granted in this environment, so the recogniser itself was
stubbed; every code path below is the shipped code.

| Check | Result |
|---|---|
| Start sets `continuous`/`interimResults` true | Pass |
| Interim text renders in preview, never in the answer field | Pass |
| Final text commits to the answer field; word count updates via the typed path's `input` event | Pass |
| Hand-edit mid-dictation preserved; later speech appends | Pass |
| 10s silence auto-stop | Pass — stopped 10s after last speech |
| Countdown appears in the final seconds | Pass — 3s/2s/1s/0s observed |
| Second click stops | Pass |
| Escape stops | Pass |
| Switching mode stops the mic and keeps the transcript | Pass |
| `not-allowed`, `audio-capture`, `network`, unknown codes | Pass — each visible **and** announced; typed answer intact |
| `no-speech` / `aborted` stay unsurfaced and listening continues | Pass |
| Unsupported browser: `aria-disabled`, visible reason, still keyboard-reachable, typing unaffected | Pass (simulated by removing the constructors and re-running init) |
| Keyboard start → transcript → stop | Pass |
| Theme switch during active listening preserves listening, transcript, and preview | Pass |
| No console errors | Pass |
| No horizontal overflow at 390px | Pass |
| Touch target 186×53 CSS px | Pass (≥44×44) |

## Committed screenshots

All images are in `evidence/`, regenerable with `evidence/capture_evidence.py`
against a local app on port 5077.

| File | Shows |
|---|---|
| `01_listening_desktop_5A_light.png` | Listening state, desktop 1280, 5A light |
| `02_listening_desktop_5C_dark.png` | Listening state, desktop 1280, 5C dark |
| `03_listening_mobile390_5A_light.png` | Listening state, 390px, 5A light |
| `04_listening_mobile390_5C_dark.png` | Listening state, 390px, 5C dark |
| `05_permission_denied_desktop_5A_light.png` | Permission-denied truthful state; typed answer intact; control reset |
| `06_composer_row_D2_desktop_5A_light.png` | D-2 close-up: relocated control beside Submit answer (cropped from 01, same render) |

### How they were captured, exactly

Headless Chrome loads the **real server-rendered** `/interview-studio?mode=me`
HTML with two additions: a `<base>` tag so assets resolve to the running app,
and a `SpeechRecognition` stub installed before `interview-studio.js` runs. A
small driver then clicks the real control and feeds real result/error events.
The template, CSS, JavaScript, and state machine are the shipped code; only the
recogniser is stubbed, because a microphone grant is impossible headless.

Chrome enforces a **500 CSS px minimum window width**, so a `--window-size=390`
capture silently lays the page out at 500 and crops — which produced clipped,
misleading first attempts. The 390px images are therefore rendered inside an
exactly-390px iframe and cropped, giving the inner document a genuine 390px
layout viewport for media queries. The committed mobile images match what the
interactive browser at 390px showed.

The clipped mode navigation at the right edge of the 390px images is
pre-existing released behaviour (a horizontally scrollable mode row), not
introduced here.

## Deviations from the released implementation

**D-1 — listening colour changed from error red to gold.** The released
`.is__mic.is-listening` used `var(--is-error)`. The 5A/5C authority reserves red
for true errors and assigns gold to "progress/current-state cues". Listening is
a current-state cue, so it now uses gold in both themes. The Video Practice
recording badge keeps its own recording red, which is correct for an actual
recording. **Requires Pete's visual acceptance.**

**D-2 — control relocated.** The dictation button moved from the side-column
"Answering aid" card to the composer action row beside Submit answer. The side
card now points to it. This is the fix for the reported absence: the side column
reflows below the composer under `max-width: 72rem`, so the control was
invisible on a phone. The Studio is otherwise unchanged.

**D-3 — Interview AI question dictation now appends instead of replacing.**
Required by continuous mode: replacing the field on each result would delete
everything said before it.

## Limitations

- Real microphone permission and real vendor transcription were not exercised;
  no browser in this environment can grant them non-interactively.
- The unsupported-browser rendering was produced by removing the constructors
  and re-running module init, not by loading Firefox.
- Chrome/Edge send audio to the browser vendor's speech service. No audio
  reaches PeerSlate, which is what the UI claims; the UI does not claim the
  audio never leaves the device.

## Open gates

- Pete's visual acceptance of the real result in both themes, including D-1.
- Homepage-parity assessment: `templates/partials/homepage/_interview_demo_scene.html`
  states "Dictation is optional in the real Studio — speak and it transcribes
  into the answer box." That remains truthful, but the walkthrough does not show
  the 10-second silence behaviour or the new placement. Parity is **open** and
  belongs to the designated manager's sequencing, not to this branch.
- No pull request has been opened.
