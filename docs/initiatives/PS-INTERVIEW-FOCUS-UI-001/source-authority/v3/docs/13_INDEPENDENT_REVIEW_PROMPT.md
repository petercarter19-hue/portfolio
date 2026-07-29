# 13 — Independent Review Prompt

Independently review the completed `PS-INTERVIEW-FOCUS-UI-001` branch against the repository baseline, this complete v3 written handoff, and all 14 authoritative PNGs.

Do not trust the implementation report without verification. Inspect the diff, rendered states, tests, network behavior, storage behavior, media lifecycle, accessibility tree, and responsive behavior.

Specifically attempt to falsify these claims:

- typing is truly primary and each real input remains the source of truth;
- dictation is optional, explicit, same-input, and nonblocking;
- the light foundation is white and no beige/ivory/cream drift remains;
- all released routes/handlers/contracts/storage keys/auth behavior remain unchanged;
- Interview AI retains all answer bases, source labels, grounding evidence, compare, follow-up, and Practice This Answer behavior;
- Interview AI was not replaced by generic chat and does not imply private-history access;
- Video Practice requests permission only after explicit action;
- camera/microphone tracks, recorder, timers, blobs, and object URLs are cleaned up safely;
- no audio/video is uploaded or persisted beyond released behavior;
- transcript coaching sends only expected text and is not mislabeled as video analysis;
- no pace, eye-contact, filler-word, confidence, clarity, or other unsupported analysis is implied;
- inactive future states are absent visually and from accessibility traversal;
- failure preserves the relevant answer, question, selected basis, generated result, recording/playback, or transcript;
- mobile sticky/dock/drawers/camera controls do not cover or lose content;
- dark mode is a token twin, not a separate implementation;
- no unsupported account history, sync, upload, analytics, publication, or employer prediction is implied.

Return PASS, PASS WITH FINDINGS, or FAIL, with concrete file/line/state/network evidence and required corrections. Do not merge or deploy.
