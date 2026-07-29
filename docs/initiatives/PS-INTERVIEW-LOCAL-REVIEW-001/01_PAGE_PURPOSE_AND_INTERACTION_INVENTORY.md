# Page purpose and interaction inventory

## Shared Interview Studio purpose

Help a visitor practice, study, and rehearse interview questions with clear
source boundaries, minimal friction, and an honest browser-local baseline.

## Shared session setup

- Edit Session occupies the same left-column width as the active task card.
- The right rail begins beside Edit Session instead of below it.
- Experience, family, and session selects open from their visible text or
  chevron hit area, work by keyboard, and remain legible in both themes.
- Interview AI does not show a redundant Answer Basis select in Edit Session.
  Its answer-source choices remain in the mode workspace.

## Shared current-question controls

- The current question is presented as a large heading.
- Its metadata and two compact actions share the row below progress:
  `Different question` and `Create question`.
- Different question randomly replaces the unanswered current question from the
  selected experience/family pool. It does not count as a completed answer and
  avoids repeats until the eligible pool is exhausted.
- Create question opens one centered modal. The visitor can type or dictate a
  question, press Enter to use it, or press Shift+Enter for a paragraph. On
  submit it becomes the current large question and the modal closes.
- Custom questions remain browser-local for the session. A future moderated
  question-bank submission flow is deferred.

## Interview Me

- Remove the old New Question row below the composer actions.
- Keep Dictate and Review My Answer together.
- Up Next remains available.
- Need a nudge opens two or three AI-generated, question-specific hints without
  inventing a candidate story.
- Need an example opens Interview AI with the same current question.
- First coaching failure preserves the answer and exposes a reliable retry.
- After review, Next Question is centered in the main reading path.
- After Improve Answer, show a compact Make it yours area with explicit options
  to use relevant approved public history and add more answer context. Never
  silently replace the visitor's original wording.

## Interview AI

- Use the same active-question presentation and Different/Create controls as
  Interview Me.
- The custom question input is visible only inside the Create Question modal.
- Keep the right-side source choices for best practice, approved public
  history, and compare; remove the redundant Edit Session Answer Basis field.
- Enter submits question and follow-up text; Shift+Enter creates a new line.
- Go to Follow-up reveals, scrolls to, emphasizes, and focuses the actual
  follow-up workspace.
- Follow-ups inherit the server-signed source mode. Generic follow-ups never
  receive or expose a grounded profile answer.

## Video Practice

- Use the same Different/Create question controls.
- The right rail contains Device Status, Public Demo Profile, Up Next, and Need
  a Nudge.
- Camera and microphone permission, recording, stopping, local playback,
  retaking, and discarding have visible states. Playback includes recorded
  audio when the browser/device provides an audio track.
- Transcript dictation uses the shared speech path and preserves text through
  errors, stops, question changes, and mode exits.

## Shared microphone contract

- Supported fields: Interview Me answer, custom question, Interview AI
  follow-up, Video transcript, plus local Video camera/microphone recording.
- Preserve typed text and insert recognized speech at the cursor where possible.
- Show requesting/listening/recording/stopping/denied/busy/unsupported/no-speech
  and retry guidance in the visible workspace.
- A second click or Escape stops dictation. Mode/question changes flush visible
  interim text before changing context.
- Never leave recognition, camera tracks, microphone tracks, timers, blobs, or
  stale events active after the owning mode or dialog closes.

## Responsive order

At narrow widths, keep the task first, then its contextual actions and privacy
or source truth in the same reading order. Do not create a permanent navigation
layer.
