# PS-INTERVIEW-LOCAL-REVIEW-001

Status: Active production release
Owner/acceptance authority: Pete
Manager/writer: Codex
Base: `origin/main` at `3da1f747609b6529542be2416649a8fba75abd49`
Release authority: On July 29, 2026, after the local implementation and browser
review pass, Pete replaced the local-only gate with: "I'm not gonna be able to
see this locally after all ... push this live." This authorizes the bounded
Candidate, Azure pull request, production pipeline, and live-verification path.

## Purpose

Implement Pete's July 29, 2026 Interview Studio review as one bounded release
across Interview Me, Interview AI, and Video Practice. The owner initially
requested a complete local preview, then explicitly activated production
release after the implementation and automated/browser review pass.

The owner-directed interaction inventory in
`01_PAGE_PURPOSE_AND_INTERACTION_INVENTORY.md` is the controlling implementation
brief for this preview. Existing production Interview visual authorities remain
the baseline for all unchanged regions.

## Owned runtime surfaces

- `templates/interview_studio.html`
- `templates/partials/interview_question_bank.html`
- `static/css/interview-studio.css`
- `static/js/interview-studio.js`
- Interview-only routes and validators in `app.py`
- Interview-only tests in `tests/test_interview_studio.py`

## Explicit exclusions

- Work, Profile, Candidate, Journal, homepage, shared navigation, and other
  non-Interview product surfaces
- account/private-history retrieval, cloud media storage, upload, or sync
- silently saving AI output or custom questions as canonical PeerSlate truth
- Work, Profile, and homepage runtime or visual changes

## Truth and safety contracts

- Drafts and session history remain browser-local.
- Interview text reaches PeerSlate only through an explicit coaching, nudge, or
  model-answer request.
- Dictation uses the browser speech-recognition capability. Interview Me,
  Interview AI, custom-question, follow-up, and transcript dictation do not
  retain audio.
- Video Practice records camera and microphone locally for in-page playback;
  media is not uploaded or retained by PeerSlate.
- Public-profile examples use only approved public evidence. Generic examples
  are labeled illustrative and use no profile evidence.
- AI proposes; the visitor chooses whether to use or edit any output.

## Release gate

Before production, run focused and full repository tests and inspect the three
modes in light and dark themes at desktop and mobile widths. Keyboard,
dropdown, dialog, retry, dictation-state, and local recording/playback behavior
must be covered. Obtain a fresh independent exact-diff review, queue the exact
reviewed branch/SHA through package-specific Candidate admission, verify
Candidate deploy/smoke/stop, merge only through an Azure pull request, then
verify the exact production pipeline and live public routes/assets. Microphone
hardware permission and audible playback require a real-browser/manual check
where automation cannot grant or hear the device.
