# 08 — Implementation Sequence and Commit Plan

## Phase 0 — discovery and baseline

Map routes, templates, styles, scripts, handlers, local-storage keys, network contracts, AI grounding and follow-up logic, media lifecycle, theme, and tests. Capture current-state screenshots and baseline results for Interview Me, Interview AI, Video Practice, and History. No UI edits.

## Phase 1 — shared semantic shell

Introduce or refactor the shared InterviewStudioShell, ModeSelector, SessionSummary, WorkspaceGrid, ContextRail/MobileDrawer, tokens, and focus primitives using the existing stack. Preserve route ownership and business handlers.

## Phase 2 — Interview Me focused stage

Implement the type-first QuestionStage and AnswerComposer; integrate optional dictation; place processing, review, improve, and failure in the same stage geometry; move queue/example/settings into contextual surfaces.

## Phase 3 — Interview AI complete flow

Apply Screen 06 geometry and `14_INTERVIEW_AI_IMPLEMENTATION_CONTRACT.md` to all real Interview AI states:

- empty/question drafting;
- answer-basis selection;
- optional dictation;
- generation/loading;
- best-practice/public-history/compare results;
- reasoning and evidence;
- no-grounding/failure;
- follow-up;
- Practice This Answer transfer;
- New Question.

Do not stop after restyling only the success screen.

## Phase 4 — Video Practice complete flow

Apply Screen 07 geometry and `15_VIDEO_PRACTICE_IMPLEMENTATION_CONTRACT.md` to all real media states:

- camera off/requesting/denied/unavailable;
- preview ready;
- recording/stopping;
- playback;
- retake/discard/new question;
- device settings;
- transcript drafting/submission/coaching/failure;
- route-exit cleanup;
- honest no-analysis/local-only truth.

Do not stop after restyling only the active-recording screen.

## Phase 5 — History integration

Apply shared shell and white hierarchy to History while preserving browser-local filters, goals, details, deletion, and storage-unavailable behavior.

## Phase 6 — white visual tokens and dark parity

Apply scoped white/navy/cobalt/teal treatment using existing token architecture. Do not globally redesign unrelated PeerSlate areas. Implement dark-token parity with identical DOM, actions, and responsive order.

## Phase 7 — responsive behavior

Implement tablet rail collapse, mobile question continuity, mobile AI basis/source disclosures, mobile camera controls, orientation/keyboard-safe layouts, and mobile sheets.

## Phase 8 — tests and visual evidence

Run complete regressions, deterministic state captures, accessibility checks, storage/network/media truth checks, and side-by-side/overlay review. Include all modes and all states listed in `17_ALL_MODE_TEST_AND_ACCEPTANCE_MATRIX.md`.

## Suggested commit boundaries

1. Discovery record and fixtures only.
2. Shared shell and tokens.
3. Interview Me structure and states.
4. Interview AI complete flow.
5. Video Practice complete flow.
6. History and cross-mode responsive behavior.
7. Accessibility, tests, and visual evidence.

Adapt to repository conventions, but keep changes reviewable and avoid unrelated cleanup.
