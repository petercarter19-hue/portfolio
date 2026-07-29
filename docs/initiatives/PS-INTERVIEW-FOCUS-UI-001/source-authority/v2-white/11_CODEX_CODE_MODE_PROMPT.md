# 11 — Ready-to-Paste Codex Code Mode Prompt

Use this only after the Ask-mode plan has mapped the real repository and reported no blocking conflict.

---

Implement `PS-INTERVIEW-FOCUS-UI-001` using the approved repository-grounded plan and the complete initiative package at `docs/initiatives/PS-INTERVIEW-FOCUS-UI-001/`.

Before editing, re-read the applicable `AGENTS.md`, confirm the authoritative baseline, confirm the dedicated branch/worktree and single-writer file ownership, and record the start SHA. Preserve all unrelated local changes, worktrees, branches, and stashes.

Mission: implement the approved Interview Focus Stage UI exactly in spirit and structure while preserving all released functionality. The current question, type-first editable answer, optional dictation, save/word status, and primary coaching action must become one visual center. Existing supporting features must move to the right moment through progressive disclosure rather than being removed.

Hard constraints:

- UI/UX-only refactor.
- No backend, API route, payload/response, AI prompt/rubric/score, database, auth, Azure, storage-key, or product-semantic changes.
- No new frontend framework, component library, build system, or unnecessary dependency.
- Reuse the real PeerSlate global shell, current design system, current theme mechanism, current state machine, current handlers, and current tests.
- Preserve Interview Me, Interview AI, Video Practice, History, session setup, queue, custom/new questions, autosave, dictation, coaching, failure recovery, review, improve, retry/next, automatic browser-local history, theme retention, and media truth.
- Do not add account-backed save, cloud history, cross-device sync, upload, video analytics, publication, or private-Slate claims.
- Light and dark must use one semantic DOM/state/action system.
- Light theme must use the approved pure-white/cool-gray/navy/cobalt/teal authority; do not preserve or reintroduce beige, ivory, cream, tan, gold, or amber selected-state styling.
- Typing is the default and visually primary input; `Use dictation` is an optional secondary control that writes into the same canonical answer.
- The `visual-authority/` folder contains exactly fourteen product screens; do not seek or invent a fifteenth visual.
- Inactive future-state panels must not remain visually or programmatically exposed.
- Do not merge or deploy.

Implement in the documented phases and commit coherently. After each phase, run the relevant existing tests and capture the required state screenshot. When a mockup label conflicts with current behavior, preserve the real behavior and report the copy decision; do not invent functionality.

Use deterministic test fixtures/interception for visual states without changing production behavior. Validate all required desktop, tablet, mobile, dark, zoom, reduced-motion, permission-denied, failure, long-content, and local-storage-unavailable states.

Before finishing:

1. run the complete required regression suite;
2. compare implementation screenshots with all visual references through overlays or side-by-side review;
3. inspect network traffic to prove answers are sent only on explicit coaching submit and no audio/video is uploaded;
4. inspect the final diff for accidental backend/global/unrelated changes;
5. perform a skeptical self-review for state loss, duplicate handlers, hidden accessibility content, focus errors, mobile overlap, public/private truth drift, and fabricated states;
6. correct all findings before reporting completion.

Final response must contain:

- full technical record: branch/worktree/start and end SHA/files/commands/tests/results/screenshots/known limitations/rollback/PR summary;
- separate plain-English owner report: what changed, what stayed the same, why it is easier, limitations, exactly one next step, and anything Pete must do;
- a clear statement that no merge or deployment occurred.

Stop and report rather than improvising if the actual repository requires a prohibited architecture or functionality change.

---
