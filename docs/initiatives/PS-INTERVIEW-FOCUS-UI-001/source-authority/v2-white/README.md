# PeerSlate Interview Studio — Focus Stage UI Implementation Handoff — White Authority v2.0

**Proposed initiative ID:** `PS-INTERVIEW-FOCUS-UI-001`  
**Prepared:** July 28, 2026  
**Owner direction:** Approved for repository inspection and implementation planning; implementation remains UI/UX-only and must preserve released functionality.  
**Primary route:** Existing public Interview Studio route and its existing deep links. Do not create a replacement product or parallel route.

## Bottom line

This package converts the approved mockup series into a repository-ready implementation contract for Codex.

The requested change is **not** a product rewrite. It is a focused presentation and interaction refactor that makes the current Interview Studio easier to understand and use while preserving its routes, endpoints, local-storage behavior, AI behavior, media behavior, failure recovery, and public-demo truth.

The controlling experience is the **Interview Focus Stage**:

> The current question, the type-first editable answer, optional dictation control, and the next primary action remain in one visual center. Supporting information waits until it is needed.

## Controlling visual decision

The previous beige/ivory direction is retired. The light theme must use a pure white page foundation, white primary surfaces, cool-gray supporting surfaces, deep navy typography, cobalt-blue interaction emphasis, and restrained teal status accents. No implementation artifact may use the retired beige/gold mockups as visual authority.

## Best handoff sequence

OpenAI's current Codex guidance recommends a two-step workflow for substantial changes: start in **Ask mode** with a repository-grounded implementation plan, then switch to **Code mode** with that plan. This package is organized for that exact sequence.

1. Place this folder in the repository under the current initiative/documentation convention, ideally:
   `docs/initiatives/PS-INTERVIEW-FOCUS-UI-001/`
2. In Codex **Ask mode**, paste `10_CODEX_ASK_MODE_PROMPT.md`.
3. Review Codex's discovered file map and conflict report. No design translation should be required from Pete.
4. In Codex **Code mode**, paste `11_CODEX_CODE_MODE_PROMPT.md`.
5. Require the screenshots, tests, technical record, and plain-English owner report defined in this package before review.

## Read order

1. `00_CODEX_START_HERE.md`
2. `01_OWNER_INTENT_AND_SCOPE.md`
3. `02_AUTHORITY_AND_CONFLICT_RULES.md`
4. `03_FUNCTIONALITY_PRESERVATION_MATRIX.md`
5. `04_INFORMATION_ARCHITECTURE_AND_LAYOUT.md`
6. `05_COMPONENT_CONTRACTS.md`
7. `06_STATE_MACHINE_AND_INTERACTION_CONTRACT.md`
8. `07_RESPONSIVE_THEME_ACCESSIBILITY.md`
9. `08_IMPLEMENTATION_SEQUENCE_AND_COMMIT_PLAN.md`
10. `09_TEST_VISUAL_QA_AND_ACCEPTANCE.md`
11. `10_CODEX_ASK_MODE_PROMPT.md`
12. `11_CODEX_CODE_MODE_PROMPT.md`
13. `12_CLOSEOUT_AND_PR_TEMPLATE.md`
14. `13_CODEX_INDEPENDENT_REVIEW_PROMPT.md`
15. `14_OWNER_REVIEW_CHECKLIST.md`
16. `15_CHANGELOG_WHITE_AUTHORITY.md`
17. `manifest.yaml`
18. `design-tokens.json`
19. `visual-manifest.json`

## Reference folders

- `visual-authority/` contains exactly 14 authoritative product-screen PNGs using the approved white/cobalt light palette.
- `references/prototypes/` contains static HTML prototypes for geometry inspection only.

The prototype HTML is **not production code** and its internal class/token names are not implementation requirements. Codex must not copy its fake content, routing, storage, or static state implementation. It exists only to make spacing, sizing, and component relationships measurable.

## Non-negotiable summary

- Preserve all current functionality and the exact answer → coaching → review → improve → retry/continue flow.
- Preserve Interview Me, Interview AI, Video Practice, History, session setup, custom/new questions, dictation, browser-local drafts/history, public-profile grounding, failure recovery, and theme behavior.
- Do not change backend endpoints, AI prompts, scoring logic, database schema, authentication, authorization, Azure resources, or production routing.
- Do not add account-backed persistence, cross-device sync, media upload, delivery analytics, publication, or private-Slate behavior.
- Reuse the existing PeerSlate shell and design system. Do not introduce React, a new frontend framework, or a new build system.
- Light and dark are the same DOM, state machine, actions, and responsive system.
- No merge, deployment, or production change is authorized by this package.
