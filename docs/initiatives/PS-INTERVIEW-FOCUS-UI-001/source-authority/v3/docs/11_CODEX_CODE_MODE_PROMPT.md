# 11 — Ready-to-Paste Codex Code-Mode Prompt

Implement `PS-INTERVIEW-FOCUS-UI-001` using the approved repository-grounded plan and this complete v3 all-modes handoff package.

Before editing, re-read applicable repository instructions, confirm the authoritative baseline, dedicated branch/worktree, single-writer ownership, and recorded start SHA.

Mission: implement the 14-screen Interview Focus Stage as one responsive component/state system and fully apply it to Interview Me, Interview AI, Video Practice, and History while preserving all released functionality.

Hard constraints:

- UI/UX-only refactor.
- Typing is primary wherever text is entered; dictation is optional, requires explicit activation, writes into the same real input, and never blocks typing.
- Light theme is white, not beige/cream/ivory; use documented white/navy/cobalt/teal direction.
- No backend, endpoint, payload/response, AI prompt/rubric/score/grounding, database, auth, Azure, storage-key, route-semantic, or media-contract changes.
- No framework/component-library/build-system migration or unnecessary dependency.
- Preserve Interview Me, Interview AI, Video Practice, History, setup, queue, custom/new question, autosave, dictation, coaching, failure recovery, review, improve, retry/next, browser-local history, theme retention, and media truth.
- Interview AI must preserve best-practice, approved-public-history, compare, source labels, reasoning/evidence, follow-up, and Practice This Answer. Do not convert it to generic chat.
- Video Practice must preserve explicit permissions, local preview/record/playback/retake/discard, device settings, transcript coaching, cleanup, and no-upload/no-analysis truth.
- No account-backed save, cloud history, cross-device sync, media upload, unsupported video analytics, private-history access, publication, or private-Slate claim.
- Light/dark use one semantic DOM/state/action system.
- Inactive future-state panels are not visually or programmatically exposed.
- Do not merge or deploy.

Implement in documented phases with coherent commits. Do not consider Phase 3 complete after only restyling the Interview AI success screen, and do not consider Phase 4 complete after only restyling the Video recording screen. Cover every state in docs 14–17.

Use deterministic fixtures/interception for visual states without changing production behavior. Validate all required desktop/tablet/mobile/dark/zoom/reduced-motion/permission/failure/long-content/storage-unavailable states.

Before finishing, run full regression; compare captures with all 14 references; inspect network traffic to prove submit/media truth; inspect storage keys, MediaStream/MediaRecorder cleanup, AI grounding labels, and final diff; perform a skeptical accessibility/state-loss/mobile-overlap review; correct findings.

Final response must contain a technical record and a separate plain-English owner report for each mode, plus an explicit no-merge/no-deploy statement.
