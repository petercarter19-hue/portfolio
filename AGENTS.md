# PeerSlate Repository Instructions

> **MANDATORY PRE-WORK GATE**
> Before any analysis that may lead to a write, code change, migration, deployment, or product decision, open and follow [START_HERE.md](START_HERE.md). Synchronize from authoritative `origin/main`, then read [CURRENT_BASELINE.yaml](docs/governance/CURRENT_BASELINE.yaml), [CURRENT_STATE.md](docs/governance/CURRENT_STATE.md), [ACTIVE_INITIATIVES.md](docs/governance/ACTIVE_INITIATIVES.md), the current Bible and Roadmap named by the baseline, and the assigned initiative package. Stop rather than guess when any pointer, scope, or ownership record is unclear. Every material closeout must use [OWNER_TECHNICAL_COMPLETION_REPORT.md](docs/templates/OWNER_TECHNICAL_COMPLETION_REPORT.md).

This file is the always-on instruction router. Product specifications, design details, and initiative scope belong in their authoritative documents rather than being duplicated here.

## Authority and precedence

- Azure DevOps `origin/main` is the authoritative repository history. GitHub is a backup mirror only, subject to the authorization recorded in `CURRENT_BASELINE.yaml`.
- Follow the precedence rules in [DOCUMENT_CONTROL.md](docs/governance/DOCUMENT_CONTROL.md). Do not hardcode a Bible or Roadmap version here; use the versions named in `CURRENT_BASELINE.yaml`.
- Use `CURRENT_STATE.md` for verified present-tense truth and `ACTIVE_INITIATIVES.md` for current ownership. The assigned initiative package controls its bounded implementation scope.
- If instructions conflict, a required document is missing, or another active lane owns the same files, stop and report the conflict. Do not invent a compromise.

## Roles and ownership

Read [AI_WORKFLOW.md](docs/AI_WORKFLOW.md) before material work and use [AI_MODEL_AND_ROLE_ROUTING.md](docs/AI_MODEL_AND_ROLE_ROUTING.md) to select the working surface.

- One package-designated manager coordinates each initiative. The manager may run in ChatGPT Work/Codex or Claude Co-Work, as recorded in the package.
- Only one active writer may own a file or mutable surface at a time. Do not edit files reserved by another lane.
- Writers are self-managed for bounded implementation, testing, documentation, and handoff. Product acceptance, visual acceptance, deployment authority, and scope changes remain with the owner or designated manager.
- Keep work on a short-lived task branch. Never push directly to `main`. Handoffs must identify the exact branch, commit, changed files, tests, and remaining decisions.
- Follow the lean delivery policy in `docs/AI_WORKFLOW.md`: perform each distinct responsibility once, use architecture and independent review only when their defined risk triggers apply, and retain the required tests, acceptance, release, and audit evidence. Packages name stable roles; `docs/AI_MODEL_AND_ROLE_ROUTING.md` is the central model-version authority.
- Owner decision, 2026-07-24: ChatGPT is the sole creator of new or materially revised PeerSlate production-intent visual authority. Existing Pete-locked authorities remain valid until materially revised. Codex and Claude writers may implement the exact locked authority, capture implementation evidence, and make documented non-material accessibility, truth, and reflow adaptations, but they may not originate or substitute visual designs. A material visual-direction change returns to the ChatGPT visual-creation lane and Pete for a new exact lock before implementation continues.

## Always-on product and trust invariants

These rules apply to every feature and surface:

- PeerSlate is a reusable multi-user product. Pete is fixture content, not product logic. Do not hardcode a single person, profile, career, tenant, or story into shared behavior.
- User content is private by default. Identity and ownership must be server-derived, and authorization must be checked before protected data is returned or changed.
- Canonical user truth, source evidence, AI proposals, and derived projections are different data classes. Preserve their provenance and do not silently collapse one into another.
- AI proposes; people decide. AI output must not silently save, publish, send, delete, apply, or become canonical truth.
- Keep one authoritative source for each fact and derive projections from it. Avoid competing truth stores and duplicated workflow state.
- The core experience must remain understandable and useful when AI is unavailable.
- Never represent fixture, seeded, demo, locally inferred, or flag-disabled behavior as verified live behavior.
- Preserve unrelated work, secrets, production data, and user-authored content. Use the least destructive implementation that meets the approved scope.

## Task-specific document router

Read only the additional authority relevant to the work:

| Work area | Required authority |
|---|---|
| Shared implementation and site behavior | [PEERSLATE_SITE_RULES.md](docs/PEERSLATE_SITE_RULES.md) and the assigned initiative package |
| User-facing UI or visual changes | [OWNER_VISUAL_INTEGRITY_STANDARD.md](docs/governance/OWNER_VISUAL_INTEGRITY_STANDARD.md), the package-named visual authority, and the required visual evidence. Apply the documented homepage parity check whenever a change can affect the homepage or shared shell. |
| Story composition or presentation | [OWNER_STORY_COMPOSITION_STANDARD.md](docs/governance/OWNER_STORY_COMPOSITION_STANDARD.md) and the assigned Story package |
| Capture, Save Moment, or Journal | [PS-JOURNAL-001](docs/initiatives/PS-JOURNAL-001/README.md) and its linked documents |
| Projects | [PS-PROJECTS-001](docs/initiatives/PS-PROJECTS-001/README.md) and its linked documents |
| Living Résumé or Slate Board | The assigned package plus [PeerSlate_Design_Bible_v0.3.md](docs/peerslate/PeerSlate_Design_Bible_v0.3.md), [PS-FEAT-001_Living_Resume_Voice_Blueprint.md](docs/peerslate/PS-FEAT-001_Living_Resume_Voice_Blueprint.md), [PeerSlate_Product_Backlog.md](docs/peerslate/PeerSlate_Product_Backlog.md), and [PS-EXP-002_Slate_Focus_Stage_Experiment.md](docs/peerslate/PS-EXP-002_Slate_Focus_Stage_Experiment.md) |
| Navigation or owner context rail | The applicable navigation rules in `PEERSLATE_SITE_RULES.md` and [OWNER_CONTEXT_RAIL_STANDARD.md](docs/governance/OWNER_CONTEXT_RAIL_STANDARD.md). Do not establish a new permanent navigation layer without approved route authority. |

When a package links a more specific contract, fixture, decision record, or acceptance checklist, that linked artifact is part of the task authority.

## Delivery guardrails

- Fetch `origin/main` before work and again before merge. Branch from the current authoritative commit and record the base SHA in the initiative evidence.
- Do not modify a dirty checkout, unrelated user changes, generated artifacts, secrets, or environment files unless the task explicitly owns them. Use an isolated worktree when needed.
- Do not add database dependencies, migrations, external services, feature flags, or compatibility layers without a documented product or technical reason inside scope.
- Keep changes reviewable and proportional. Avoid speculative refactors and do not broaden an initiative because adjacent work is convenient.
- Validate locally before handoff. Use focused tests for the changed contract and the broader repository checks required by the package or risk level.
- Do not replace a required quality control with ceremony: preserve complete-diff self-review, pre-merge verification, risk-based independent review, final visual acceptance where applicable, and runtime pipeline/live verification. Use the central audit cadence rather than adding duplicate per-slice audits.
- Merge through an Azure DevOps pull request using the repository's required squash workflow. Delete the remote task branch after verified merge.
- A successful merge is not proof of deployment. When deployment is in scope, verify the exact pipeline run and collect production evidence before reporting the work as deployed.
- Update the GitHub mirror only when `CURRENT_BASELINE.yaml` records authorization to do so.

## Quality and evidence

- Meet WCAG 2.2 AA expectations, including keyboard use, visible focus, semantic structure, contrast, motion preferences, and responsive behavior.
- Test reusable behavior with generic or multiple fixture profiles where practical; a Pete-only result is not sufficient product evidence.
- Preserve explicit loading, empty, error, unavailable, flag-off, and permission-denied states where the feature can enter them.
- Label demo and fixture experiences truthfully and keep live or backend-connected claims tied to reproducible evidence.
- User-facing work requires the screenshots, routes, viewports, and comparison evidence named by the visual standard and initiative package. Non-visual work does not require invented visual evidence.

## Closeout and communication

Use the completion-report template for every material closeout. At minimum, report:

- base and final commit SHAs;
- changed files and the reason for each;
- tests and evidence with pass/fail results;
- pipeline and production status when applicable;
- remaining risks, deferred work, and owner decisions;
- whether each claimed capability is implemented, fixture/demo only, backend-connected, flag-disabled, or deferred.

Communicate plainly. Do not call code complete, a merge deployed, a fixture live, or an AI proposal approved unless the corresponding evidence exists.
