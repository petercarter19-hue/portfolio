# 00 — Codex Start Here

## Mission

Implement the approved **PeerSlate Interview Studio Focus Stage** as one coherent frontend UI/UX refactor over the existing released product.

This is not an Interview Me-only initiative. It covers four destinations in one shared system:

1. **Interview Me** — user writes or optionally dictates, submits, receives coaching, improves, retries, or continues.
2. **Interview AI** — user asks an interview question, chooses an evidence basis, receives a clearly sourced answer, compares approaches, asks a follow-up, or sends the answer into practice.
3. **Video Practice** — user rehearses on camera locally, reviews or retakes the local recording, and may separately type, paste, or dictate a transcript for content coaching.
4. **History** — user reviews records saved only in the current browser.

The Interview Me loop remains:

> **Question → Answer → Coaching → Improve → Retry or Continue**

The Interview AI loop remains:

> **Question → Choose answer basis → Generate → Verify source and reasoning → Follow up or Practice This Answer**

The Video Practice loop remains:

> **Question → Enable devices → Record locally → Review/retake/discard → Optionally submit a text transcript for content coaching**

## Locked owner decisions

- **Typing is the primary answer method.** The editable textarea or text input is immediately usable and visually dominant where text entry is required.
- **Dictation is optional.** It writes into the same real input and never becomes a separate answer source.
- **The light foundation is white**, not beige, ivory, cream, parchment, tan, or sepia.
- The visual system is white + deep navy + cobalt + restrained teal, with red reserved for errors/destructive actions.
- The 14 PNGs are one implementation system, not alternatives.
- Screens `06` and `07` are the geometry authorities for Interview AI and Video Practice. Their full state contracts are written in `docs/14_...` and `docs/15_...`.
- No mode may be replaced with a generic chat, wizard, dashboard, or new backend workflow.

## Mandatory reading order

1. This file.
2. `01_OWNER_INTENT_AND_SCOPE.md` through `09_TEST_VISUAL_QA_AND_ACCEPTANCE.md`.
3. `14_INTERVIEW_AI_IMPLEMENTATION_CONTRACT.md`.
4. `15_VIDEO_PRACTICE_IMPLEMENTATION_CONTRACT.md`.
5. `16_SHARED_SHELL_CROSS_MODE_RESPONSIVE_CONTRACT.md`.
6. `17_ALL_MODE_TEST_AND_ACCEPTANCE_MATRIX.md`.
7. `SCREEN_AUTHORITY_MATRIX.md` and all 14 PNGs.
8. Ask-mode prompt, then repository discovery, then a repository-grounded implementation plan.

## Mandatory repository discovery before editing

1. Read repository `START_HERE.md`, every applicable `AGENTS.md`, initiative registry, current design authority, test instructions, and release governance.
2. Verify the operational source of truth; do not assume a mirror is authoritative.
3. Record branch, worktree, exact start SHA, remotes, status, stashes, and active work touching Interview Studio or shared shell files.
4. Do not clean, reset, stash, switch, overwrite, or reuse another task's worktree.
5. Create a dedicated feature branch/worktree according to repository conventions.
6. Inspect the real implementation before proposing changes: routes, templates, CSS, JavaScript, storage keys, dictation, coaching requests, Interview AI generation and grounding, follow-ups, practice transfer, History, theme, camera/microphone lifecycle, local recording, transcript coaching, dialogs, drawers, focus management, tests, and fixtures.
7. Create a repository-local discovery record and implementation plan before Code mode.

## Functional boundary

This is a **UI-only refactor**. Preserve routes, endpoints, payloads, response contracts, AI prompts, rubrics, scoring, grounding rules, storage semantics, authentication, database behavior, local-media behavior, and browser-local truth.

Allowed: semantic markup refinement, scoped component extraction in the existing stack, CSS/token work, rearranging existing controls, progressive disclosure, responsive reflow, accessibility improvements, and tests/fixtures needed to prove preservation.

Not allowed: framework migration, backend work, database migration, route replacement, account-backed history, cloud sync, audio/video upload, fabricated video analytics, private-data access in the public demo, publication, new entitlement logic, or unrelated cleanup.

## Required output

A reviewable branch/PR only. Do not merge or deploy. The final report must include technical evidence, visual evidence, accessibility evidence, network/storage/media truth evidence, rollback instructions, and a plain-English owner summary for all four destinations.
