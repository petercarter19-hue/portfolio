# PeerSlate Interview Studio — Complete All-Modes Codex Handoff v3

This package is the implementation handoff for `PS-INTERVIEW-FOCUS-UI-001`.

It covers the complete released Interview Studio surface:

- **Interview Me** — full focused question, type-first answer, optional dictation, coaching, improvement, retry, continue, and failure flow.
- **Interview AI** — full evidence-labeled answer-generation workspace, including best-practice, approved-public-history, compare, follow-up, and practice-transfer behavior.
- **Video Practice** — full local-only camera rehearsal flow, including device permission, preview, recording, playback, retake/discard, transcript coaching, and honest no-analysis boundaries.
- **History** — browser-local records and goals without account or cross-device claims.

Package truths:

- Exactly **14 authoritative product-screen PNGs** remain in `references/authoritative_mockups/`.
- Screens `06` and `07` establish the desktop geometry for Interview AI and Video Practice. Their complete state coverage is defined by `docs/14_...` through `docs/17_...`.
- `REFERENCE_INDEX_NOT_A_PRODUCT_SCREEN.png` is an index only, not Screen 15.
- Typing is primary wherever text is entered; dictation is optional and uses the same real input.
- The light foundation is clean white with deep navy, cobalt, and restrained teal. Beige, ivory, cream, parchment, tan, and sepia are prohibited.
- Existing routes, APIs, AI behavior, media behavior, storage truth, and privacy boundaries must remain intact.
- Do not merge or deploy from this handoff.

Start with `docs/00_CODEX_START_HERE.md`.
