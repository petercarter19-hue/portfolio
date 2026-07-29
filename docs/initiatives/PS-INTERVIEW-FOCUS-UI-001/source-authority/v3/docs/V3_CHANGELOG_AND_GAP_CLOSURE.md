# v3 Changelog and Gap Closure

## Why v3 exists

The v2 package contained authoritative Screens 06 and 07 and instructed Codex to apply the shared shell to Interview AI and Video Practice. That was not detailed enough to guarantee complete state implementation.

v3 closes that gap without increasing the authoritative screen count.

## Added

- Complete Interview AI architecture, state, responsive, accessibility, truth, and acceptance contract.
- Complete Video Practice permission, device, recording, playback, cleanup, transcript-coaching, privacy, responsive, and acceptance contract.
- Shared cross-mode shell and responsive contract.
- All-mode state/test matrix.
- Updated Ask-mode and Code-mode prompts requiring repository mapping and complete implementation of both modes.
- Updated implementation sequence with dedicated Interview AI and Video Practice phases.

## Authority clarification

- Screen 06 remains the Interview AI desktop geometry authority.
- Screen 07 remains the Video Practice desktop geometry authority.
- Written contracts define their additional ready/loading/failure/follow-up/permission/playback/transcript/mobile states.
- The package still contains exactly 14 authoritative product-screen PNGs.

## No scope expansion into new functionality

v3 does not authorize:

- new AI prompts, rubrics, grounding sources, or backends;
- generic Interview AI chat;
- video upload or cloud retention;
- automatic video transcription;
- delivery analytics;
- account-backed History;
- merge or deployment.
