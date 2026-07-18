# PS-INTERVIEW-PUBLIC-GATE-001 — Interview Studio Public Gate and Progressive Layering

## Assignment

- Writer: Claude Code
- Manager/reviewer: ChatGPT Work
- Branch when accepted: `work/YYYY-MM-DD-interview-public-gate-001`
- Entry gate: PS-NEXT-WAVE-MANAGER-001 is squash-merged, its Azure pipeline is green, and the branch starts from the resulting current `origin/main`.
- Depends on: PS-INTERVIEW-002, PS-RESUME-PUBLIC-REFINE-001, and the verified public/auth route audit.

## Outcome

Make the existing Interview Studio an unmistakably honest public demonstration. A visitor must understand which public profile is grounding an answer, what is stored only in this browser, what is sent to PeerSlate for coaching, what camera/voice behavior remains local, and that account-backed private practice is a future authenticated workspace rather than a feature on the public route.

This package also improves progressive layering so the public Studio opens with one clear practice choice and reveals settings, history detail, secondary controls, and deeper explanation only when useful. It is a focused refinement, not a new Studio, authentication project, or backend persistence system.

## Route and identity decision

- `/interview-studio` remains the public demonstration route.
- `/interview-studio/history` remains public and may show only records stored in the current browser for the public demonstration.
- Existing legacy aliases continue to redirect to `/interview-studio`.
- `/app/interview-studio` is reserved for a future authenticated owner workspace. This Claude package must not create, link to as working, or simulate that route.
- Public “Use history” behavior may use only the published profile data already supplied by the server. It must identify the public profile by name and never imply access to the visitor's private history.

## Acceptance criteria

1. The opening clearly says this is public practice and identifies the public profile used for any history-grounded example.
2. The visitor can distinguish “practice as yourself” from “generate an example using this public profile.” Generic best-practice output remains explicitly illustrative.
3. Drafts, goals, and completed-attempt records on the public route are labeled as current-browser data, not an account, private cloud history, or cross-device sync.
4. The settings/privacy explanation states when the active question and submitted answer are sent to PeerSlate for coaching. Camera recording remains local and unretained; microphone behavior is described accurately for the implemented browser path.
5. The default view has one dominant practice object. Secondary configuration and history depth use accessible progressive disclosure without hiding essential truth labels.
6. Written practice, model-answer modes, compare behavior, browser-local history, camera rehearsal, legacy redirects, and existing API failure states continue to work.
7. No public page exposes private Capture/Moment/member data, and no public action writes to Capture, Moment, Journal, résumé, or another canonical surface.
8. Keyboard, visible focus, screen-reader names/states, 200% zoom, reduced motion, 390×844 mobile, unavailable-media fallbacks, and no-JavaScript truthfulness are reviewed.
9. Focused Interview Studio tests, navigation/site rules, governance guardrails, and the complete configured suite pass.

## Writable files

- `templates/interview_studio.html`
- `static/css/interview-studio.css`
- `static/js/interview-studio.js`
- `tests/test_interview_studio.py`
- package-specific screenshots under `artifacts/ps-interview-public-gate-001/`
- This initiative directory and its completion report

If implementation requires another file, stop and ask the manager to reserve it before editing.

## Read-only and forbidden domains

- Treat `app.py`, public API endpoints, route registration, entitlement resolution, public profile data, and shared base/navigation files as read-only.
- Do not create authenticated routes, sessions, server persistence, migrations, database calls, private history, or account sync.
- Do not touch Capture, Moment, Journal, résumé, owner templates/styles, global theme tokens, navigation, deployment configuration, or backend tests.
- Do not claim privacy merely because data is in browser storage; explain the actual boundary.
- Do not add a fake sign-in destination, disabled owner workspace, second profile dataset, or invented member activity.

## Required reading

Follow `START_HERE.md`, then read the current governance records, Document Control, Bible/Roadmap/Sync Standard, `docs/PEERSLATE_SITE_RULES.md`, PS-INTERVIEW-002, [route and truth boundary](01_BOUNDARY_CONTRACT.md), [experience/accessibility contract](02_EXPERIENCE_ACCESSIBILITY.md), [validation plan](03_VALIDATION_PLAN.md), and [implementation sequence](04_IMPLEMENTATION_PLAN.md).

Close with `docs/templates/OWNER_TECHNICAL_COMPLETION_REPORT.md` and the exact branch plus full commit SHA.
