# PS-INTERVIEW-MIC-001 — Speak-your-answer architecture decision

_Written 2026-07-20, before any product code was changed._
_Branch `work/2026-07-20-interview-me-microphone-001`, base `origin/main` at
`ed3409a902f38e9437f6fbf70d3f2f61625037f4`._

**Package ID `PS-INTERVIEW-MIC-001` is proposed by the writer and requires
designated-manager ratification.** No shared governance record
(`CURRENT_BASELINE.yaml`, `CURRENT_STATE.md`, `ACTIVE_INITIATIVES.md`) is edited
by this branch.

---

## 1. Owner request

Pete, 2026-07-20:

> "There's no microphone option in Interview Me. Not only create one but make
> sure it works like everything else. When a person clicks on it, it should run
> until they click off of it or there are ten seconds of silence."

Pete called the absence "a huge miss."

## 2. What the repository actually contains — correction to the premise

The premise "there is no microphone option" is **materially true as an
experience and false as a matter of markup.** Both halves matter.

A dictation control already ships in the released Studio
(`interview_studio_pr_101` / `39002f5130a1766d2090007c16582e0dbe07226c`):

| Location | Hook | Field |
|---|---|---|
| `templates/interview_studio.html:446` | `data-is-mic="answer"` | Interview Me answer textarea |
| `templates/interview_studio.html:504` | `data-is-mic="ai"` | Interview AI question input |
| `templates/interview_studio.html:670` | `data-is-mic="video"` | Video Practice transcript |

All three are wired to one shared helper, `startDictation()` at
`static/js/interview-studio.js:1121`, which already uses
`window.SpeechRecognition || window.webkitSpeechRecognition`.

So why does the owner experience it as absent?

1. **It stops almost immediately.** The helper sets
   `recognition.continuous = false` and `recognition.interimResults = false`
   (`interview-studio.js:1139-1140`). With `continuous = false` the Web Speech
   API ends the session after a single utterance — roughly one sentence, then a
   short pause. A STAR interview answer runs 60–90 seconds. The control
   therefore drops out several times per answer and reads as broken.
2. **Nothing is visible while speaking.** With `interimResults = false` there is
   no on-screen evidence of capture until the utterance finalises. Between click
   and first text the control looks dead.
3. **It is placed away from the answer.** The button lives in the
   `is__side-column` "Answering aid" card, *below* the "Coaching status" card
   (`templates/interview_studio.html:444-451`). At `max-width: 72rem` the side
   column reflows underneath the composer
   (`static/css/interview-studio.css:1199-1201`), so on a 390px phone the
   microphone sits below the answer box, the submit control, and a status card.
   A visitor answering a question never sees it.

**Conclusion.** This package is not "add a microphone to a route that has none."
It is "make the Studio's existing dictation control continuous, visible, honest,
and reachable, to the standard of the rest of the released Studio." That framing
is what keeps it inside the governance boundary described below.

## 3. The decision

**Recommendation: (a) browser-native Web Speech API `SpeechRecognition`.**

Specifically: **extend the one existing `startDictation()` helper.** Do not add a
second recogniser, a second control, or a parallel code path.

**Option (b), reusing the PS-VOICE-001 server path, is rejected.** Building it
would be a major architectural change requiring explicit owner approval, and this
writer would stop and report rather than build it.

### 3.1 Governance evidence for (a)

The repository does not merely permit browser speech recognition on this route.
It **names it as the route's transcript path** and writes the failure states for
it.

`docs/initiatives/PS-INTERVIEW-PUBLIC-GATE-001/01_BOUNDARY_CONTRACT.md`, the
state-and-transmission matrix:

| State or action | Where it exists | Honest public label |
|---|---|---|
| Browser speech recognition/transcript | implemented browser capability | describe the real browser/transcript path and fallback; do not imply stored voice Capture |

`02_EXPERIENCE_ACCESSIBILITY.md:40`:

> "Do not introduce voice-Capture language. Dictation inside public practice is
> not the private Capture system."

`02_EXPERIENCE_ACCESSIBILITY.md:31` requires a typed fallback for
"missing speech recognition" — a failure state that only exists for a
browser-native implementation. A server pipeline has no such state.

`09_DUAL_THEME_VISUAL_AUTHORITY_AND_CLAUDE_BRIEF.md` puts dictation inside the
accepted visual authority: `PracticeShell` includes an "optional local dictation
control" (item 5), and screen `PUBLIC-02_ACTIVE_WRITTEN_PRACTICE` requires
"local dictation as an available aid rather than a new default."

`tests/test_interview_studio.py:669` asserts `SpeechRecognition` **is present**
in the client source. Browser-native dictation is an existing locked contract on
this route, not a new proposal.

### 3.2 The "second dictation path" warning does not apply — and shapes the design

The warning the manager cited is real but precisely scoped. From
`PS-INTERVIEW-HISTORY-SALVAGE-001/02_KEEP_DISCARD_VERDICTS.md`, verdict D-6:

> "The branch's story dialog wires `data-is-mic="story"` into the browser
> `SpeechRecognition` helper that the old Studio used for its text fields. …
> A second browser-only dictation path inside the Studio would be a second voice
> story with different privacy, retention, and failure semantics."

Read exactly, that verdict:

- concerns a **story dialog** producing a **canonical private record**, where a
  browser transcript would compete with PS-VOICE-001's audio retention and
  privacy semantics;
- **acknowledges the Studio text-field helper as the pre-existing one** ("the
  helper that the old Studio used for its text fields"); and
- forbids a **second pipeline**, not the first.

This package touches no story dialog, creates no canonical record, and persists
nothing server-side. It extends the single existing text-field helper.

The warning does, however, bind the implementation: because a *second* path is
forbidden, the correct move is to change `startDictation()` in place so all three
fields keep identical behaviour. Adding an Interview-Me-only recogniser would
itself create the second path. This is why the shared helper is edited rather
than duplicated.

### 3.3 Why (b) is wrong for this route

**Authentication.** `/interview-studio` is public and unauthenticated.
PS-VOICE-001 requires trusted-session identity and owner-scoped persistence.
`01_BOUNDARY_CONTRACT.md` reserves that for the future `/app/interview-studio`
and states plainly: *"None of that may be approximated in this front-end
package."* There is no owner to scope anonymous visitor audio to.

**Privacy.** Option (b) would upload anonymous visitors' voice recordings into
Azure Blob Storage inside the authenticated owner's private Capture
infrastructure. Today the Studio truthfully tells visitors their media stays
local. Routing public audio into private owner storage inverts that promise and
creates a retention, deletion, and consent obligation for people who never
signed in. Under Web Speech, no audio reaches a PeerSlate server at all.

**Cost.** Anonymous, unauthenticated, unbounded Azure Speech transcription on a
public marketing-adjacent route has no rate limit, no quota owner, and no abuse
control. Browser-native recognition costs PeerSlate nothing.

**Truth.** The Studio's existing truth strip claims browser-local behaviour.
Option (a) keeps every current claim accurate. Option (b) would make several of
them false in the same release.

### 3.4 Honest limitation of (a)

Chrome and Edge implement `SpeechRecognition` by sending audio to a
**browser-vendor** speech service; Safari uses Apple's. It is browser-local in
the sense that **no audio reaches PeerSlate**, which is the claim the Studio
makes and the claim the boundary contract requires. The UI must not overclaim
"nothing leaves your device." Copy will say the browser does the transcription
and PeerSlate does not receive or keep the audio. Firefox does not implement the
API at all; that is a first-class unsupported state, not a defect.

## 4. Behaviour contract (Pete's spec)

| Requirement | Implementation |
|---|---|
| Click to start | `continuous = true`, `interimResults = true` |
| Keeps listening | Auto-restart on spontaneous `onend` while the visitor still intends to listen |
| Stops on second click | Toggle; the same button stops it |
| Stops after 10s of silence | Deadline timer reset by every interim or final result |
| Transcript lands in the typed field | Final segments append to the same textarea the typed path uses |
| Editable afterwards | Only *final* segments are committed; interim text renders in a separate preview so it can never clobber the visitor's own edits |

"Clicks off of it" is also honoured beyond the toggle: leaving Interview Me,
switching mode, or submitting the answer stops the recogniser. A microphone must
never keep listening after the visitor has left the field.

## 5. Truthful states — no simulation

| State | Detection | Behaviour |
|---|---|---|
| Browser unsupported | Feature-detect at init | Persistent visible note, `aria-disabled` button that explains rather than silently failing; typing unaffected |
| Permission denied | `error === 'not-allowed'` / `'service-not-allowed'` | Exact denial message plus how to re-enable |
| Permission dismissed | **Not distinguishable** from the API | Reported honestly as "no speech captured", naming a dismissed prompt as one possible cause. No invented state |
| No speech detected | `error === 'no-speech'`, or session ended with zero final text | Says so; keeps typed text intact |
| No microphone / in use | `error === 'audio-capture'` | Exact message |
| Network failure | `error === 'network'` | Exact message |
| Other/unknown | default branch | Generic honest message, keep typing |
| Actively listening | live state | Visible pulsing control, status line, interim preview, live-region announcement |
| 10s auto-stop | deadline fired | Announced before *and* after: the rule is stated up front, a countdown appears in the final seconds, and the stop reason is announced |

The dismissed-permission row is the one place the platform cannot give us truth.
Inventing a distinct "you dismissed the prompt" state would be a fabricated
state, which the visual-integrity standard forbids. It is reported as what we can
actually observe.

## 6. Accessibility commitments

- Real `<button>`; keyboard operable by default; `aria-pressed` reflects the
  toggle; visible focus inherited from the Studio focus token.
- Discrete state changes route through the existing `[data-is-live]` region via
  `announce()`. The interim preview is **not** a live region — continuously
  changing text would flood a screen reader.
- On stop, one announcement states the reason and whether the answer box was
  updated.
- <kbd>Escape</kbd> stops an active dictation.
- Reduced motion: the listening pulse is covered by the existing
  `@media (prefers-reduced-motion: reduce)` rule; the listening state is also
  conveyed by text and colour, never by animation alone.
- Typing stays fully first-class. Dictation is an aid; every failure path leaves
  the typed answer untouched.
- Both themes: 5A Editorial Studio Ledger light and 5C Cinematic Studio dark, via
  existing semantic tokens only.

## 7. Boundaries this package will not cross

- No feature flag, schema, migration, or production setting.
- No Photo, Owner Home, Moment, Placement, or private Voice Capture code.
- No `validate_interview_review` / `validate_interview_model_answer` edits —
  another lane holds those.
- No server change of any kind. This is client + template + CSS + tests.
- No claim of account-backed history or server persistence on the public route.
- The Studio is not redesigned around the microphone.
- No PR, no merge, no push to `main`.

## 8. Decision result

**Option (a), extending the existing browser-native `startDictation()` helper.**
Implementation proceeds under that decision. This is a material user-facing
change and requires Pete's visual acceptance plus a homepage-parity assessment
before any pull request.
