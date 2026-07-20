# PS-OWNER-HOME-VIEWER-GATE-001

## Assignment

- Package: Owner Home and Viewer Architecture Gate
- Designated manager: ChatGPT Work
- Architecture-planning writer: ChatGPT Codex
- Branch: work/2026-07-19-owner-home-viewer-architecture
- Base: authoritative Azure DevOps origin/main at 31864e43287d7cefb5a0d1c0441e94bec0bd6b1f
- Later owner-direction update synchronized through current origin/main at 5cc5b69346ee354bcc36248f7ee5724ce13c9d08
- Roadmap requirements: PS-HOME-001, PS-VIEW-001, PS-PREVIEW-001, and the relevant PS-SETTINGS-001 boundary
- Status: architecture accepted by the designated manager on 2026-07-19;
  `PS-HOME-BACKEND-001` active, frontend sequenced after backend merge

## Purpose

Define an implementation-ready truth, authorization, projection, finite-content, accessibility, test, release, and decomposition baseline for a signed-in Owner Home and the owner, selected-person, connection, authenticated-member, and public viewing modes.

This is Gate B planning only. It does not implement routes, data, UI, publication, sharing, viewer access, or final visual composition.

## Governing sources

- Root START_HERE.md and docs/AI_WORKFLOW.md
- Bible v2.6 and Roadmap v2.5 named by CURRENT_BASELINE.yaml
- CURRENT_STATE.md, ACTIVE_INITIATIVES.md, and MANAGER_SESSION_HANDOFF.md
- OWNER_VISUAL_INTEGRITY_STANDARD.md
- Existing PS-AUTH-001, PS-CAPTURE-001/002, PS-MOMENT-001, and PS-PLACEMENT-001 contracts
- Existing identity/profile/entity/access/publication/connection schema foundations, treated as foundations rather than proof of viewer capability

## Reserved files

This planning branch owns only this initiative directory:

- README.md
- CURRENT_STATE_INVENTORY.md
- VISUAL_TRUTH_HANDOFF.md
- AUTHORIZATION_PROJECTION_MATRIX.md
- FINITE_HOME_CONTRACT.md
- ARCHITECTURE.md
- EXPERIENCE_ACCESSIBILITY_REQUIREMENTS.md
- TEST_RELEASE_PLAN.md
- IMPLEMENTATION_DECOMPOSITION.md
- COMPLETION_REPORT.md

No application, template, CSS, JavaScript, SQL, infrastructure, deployment, Bible, Roadmap, or shared governance file is reserved or changed.

## Gate result

The finite owner-only Home core is recommended as the first implementation slice. Broader viewer modes and My Slate preview remain gated until the proposed authorization/projection migration, real publication/grant contracts, route-map decision, and complete production-intent frontend design package are separately approved.

Owner direction added 2026-07-19: approved future capabilities should still be visibly present in the next production-intent appearance pass and eventual first UI as Voice-style capability previews: genuinely disabled, visibly labeled **Coming later**, accessible, visually complete, and free of fabricated data or working-state behavior. Backend activation remains gated.

## Fable architecture addendum (2026-07-19)

After Pete accepted the Owner Home editable authority candidate (`31864e4`),
the Claude/Fable architecture writer translated this planning package and that
accepted visual authority into a repository-specific, implementation-ready
architecture on branch `work/2026-07-19-owner-home-fable-architecture`:

- `01_FABLE_AUTHORITY_MANIFEST.md` — accepted artifacts, SHA-256 register, binding versus supporting references, known-refinement register, owner theme decision
- `02_FABLE_REPOSITORY_FEASIBILITY_AUDIT.md` — current-repository foundations, reuse map, gaps, drift from planning assumptions
- `03_FABLE_FIRST_SLICE_RECOMMENDATION.md` — finite signed-in owner-only Home; exact route and integration recommendation
- `04_FABLE_BACKEND_CONTRACT_MAPPING.md` — Codex server architecture mapped to exact repository files and tests
- `05_FABLE_FRONTEND_IMPLEMENTATION_ARCHITECTURE.md` — template/CSS/JS/test/artifact mapping, DOM inventory, states, responsive/accessibility behavior
- `06_FABLE_VISUAL_PARITY_DEVIATION_REGISTER.md` — area-by-area parity map,
  approved deviations D1–D6, and resolved manager decisions U1–U4
- `07_FABLE_FILE_RESERVATIONS_INTERSECTIONS.md` — exact package reservations, forbidden files, sequencing
- `08_FABLE_FEASIBILITY_MATRIX.md` — Pass/Conditional/Fail per component and state
- `CODEX_BACKEND_IMPLEMENTATION_BRIEF.md` — PS-HOME-BACKEND-001 writer brief
- `SONNET_FRONTEND_IMPLEMENTATION_BRIEF.md` — PS-HOME-FRONTEND-001 writer brief
- `10_FABLE_REVIEW_CHARTER_EVIDENCE_MATRIX.md` — review, evidence, and acceptance obligations
- `FABLE_COMPLETION_REPORT.md` — standard completion report for the architecture branch
- `11_MANAGER_ACCEPTANCE_AND_ACTIVATION.md` — binding U1–U6 decisions,
  release-order correction, architecture acceptance, and backend activation

The accepted authority package is preserved verbatim at
`artifacts/ps-owner-home-viewer-gate-001/authority-candidate-31864e4/`, with
the Windows generator fix documented at
`artifacts/ps-owner-home-viewer-gate-001/windows-generator-fix/`.
Architecture only: nothing is implemented, deployed, or live.

## Manager disposition (2026-07-19)

The designated ChatGPT Work/Codex manager accepted the architecture after
synchronizing it with current `origin/main`. U1–U6 are closed. The backend
package is assigned to ChatGPT Codex from a fresh post-merge branch and must
leave `/app` completely unchanged. Capture Photo PRs 95/96 and pipelines
139/140 cleared the overlapping shared-file gate; the assignment is ready. The
frontend package alone owns the later flag-on template switch and exact dark
cinematic shell. See
`11_MANAGER_ACCEPTANCE_AND_ACTIVATION.md` for the controlling decisions.

## Explicit exclusions

- No Journal, Feed, Community, Story Composer, Interview Studio, Capture Media, Voice, publication, connection, matching, or global navigation/theme implementation.
- No conversion of Pete-specific public fixtures into a claimed multi-user system.
- No final visual composition or new visual authority.
- No audience expansion or client-side authorization.
- No duplicate Capture, Moment, profile, Story, resume, or projection truth.
