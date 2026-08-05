# Independent review — OS-5 live dictation

- Reviewer: Claude Opus 5, fresh delegated session at maximum effort.
- First candidate `b7e9b30`: **APPROVE** with eleven non-blocking findings,
  three behavioral (interim speech dropped from submits because the flush ran
  after the payload reads; a second rail-lock site never flushed and was
  invisible to its own guard test; an unsupported-browser mic could be
  re-enabled into a listener-less live-looking control).
- Fix commit `a6326ab`: **APPROVE** — all eleven findings resolved, the two
  structural fixes mutation-proven, and the headline flush fix shown to also
  cover the two intake/correction submits the old placement never protected.
  Three new coverage-only findings.
- Final candidate `9533088609a6b48116fc4d60131c35159579b7d8`: the three
  coverage guards added (positional flush assertion red-proven, the
  privacy-disclosure sentence locked at a count of six, the Node extractor
  given explicit sentinels).

## What the slice is

The shared dictation module (`static/js/dictation.js`, extracted for
Interview Studio) wired live across the room's four documented mic surfaces —
six button instances: role intake; source-concern correction and whole-source
correction; per-statement clarification; and the response rail's Tell-us-more
and Provide-an-example fields. The module fix replaces four hardcoded
"10 seconds" strings with the configured silence duration; Interview Studio
passes no override, so its behavior and copy are byte-identical, locked by
its suites (227 passed) and a Node runtime regression test.

## Verified contract

Voice never submits, analyzes, saves, deletes, or navigates: the synthetic
input event reaches only DOM state sync; transcripts enter the DOM solely via
.value and textContent with no HTML sink; UUID-only keys make the attribute
selectors injection-proof; Escape, tab-switch, silence, and second-click all
stop recording; the flush now precedes every field read on every submit path.
Anonymous mode is wired identically per the handoff's explicit "Anonymous
intake is paste/type/dictate only … same screens, same flow"; the slice adds
zero server surface (app.py, routes, and services untouched). The live-mic
treatment adds exactly the M18-described outer glow to the existing halo.
Every mic help paragraph carries "Your browser does the transcribing —
PeerSlate does not receive or keep the audio."

## Recorded deferrals

- §15 acceptance item "06 Voice active" is partly deferred: no separate
  visible "Stop voice input" text control (new composition belongs to the
  visual lane); the accessible name toggles and four stop paths exist.
- dictation.js is served unversioned on this page, versioned on Interview
  Studio — matches each page's own convention; noted for cache awareness.
