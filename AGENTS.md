# PeerSlate Repository Instructions

> **MANDATORY PRE-WORK GATE**
> Before any analysis that may lead to a write, code change, migration, deployment, or product decision, open and follow [`START_HERE.md`](START_HERE.md). Synchronize from authoritative `origin/main`, then read `docs/governance/CURRENT_BASELINE.yaml`, `docs/governance/CURRENT_STATE.md`, `docs/governance/ACTIVE_INITIATIVES.md`, the current Bible/Roadmap named there, and your assigned initiative package. Stop rather than guess when any pointer or ownership record is unclear. Every material closeout must use [`docs/templates/OWNER_TECHNICAL_COMPLETION_REPORT.md`](docs/templates/OWNER_TECHNICAL_COMPLETION_REPORT.md).
>
> Authoritative versions are always the ones named in `docs/governance/CURRENT_BASELINE.yaml` (currently Bible + Roadmap v2.3).

## Mandatory shared AI and Git workflow

Before planning changes, editing files, or running Git write operations, read `docs/AI_WORKFLOW.md` in full. It is the canonical collaboration workflow for Peter, Codex, Claude, every computer, and every worktree.

Non-negotiable summary:

- `origin` is Azure DevOps and is the only source of truth.
- `github` is a backup mirror only; GitHub Actions deployment stays disabled.
- Never commit or push directly to `main`.
- Create one short-lived `work/YYYY-MM-DD-task-name` branch per task.
- Only one person or AI may actively write to a branch at a time.
- Commit and push before handoff; handoffs require the branch and exact full SHA.
- Merge through an Azure pull request using squash merge, then delete the task branch.
- Never discard unrelated work or perform destructive Git cleanup without a verified recovery reference.
- Never stage or commit machine-local configuration, credentials, or secrets.

If another document contains older Git or deployment instructions, `docs/AI_WORKFLOW.md` controls.

## Project purpose

PeerSlate is a multi-user, evidence-backed professional story and growth platform. It is not a Pete-only portfolio. Pete's content is fixture/demo data only.

## Source of truth

**v1.3 (2026-07-16):** `PeerSlate_Company_and_Product_Bible_v1.3.docx`
(repo root) and `docs/PEERSLATE_SITE_RULES.md` now govern product
direction, language, navigation, Community behavior, AI behavior, and
brand (Iris Foundry). Where older documents below conflict with them,
v1.3 wins — report the conflict. Version 1.2 remains in the repository
as the prior decision record.

Before changing résumé or Slate Board code, read these repository documents in this order:

1. `docs/peerslate/PeerSlate_Design_Bible_v0.3.md`
2. `docs/peerslate/PS-FEAT-001_Living_Resume_Voice_Blueprint.md`
3. `docs/peerslate/PeerSlate_Product_Backlog.md`
4. `docs/peerslate/PS-EXP-002_Slate_Focus_Stage_Experiment.md`

If any source document is missing, stop and report the missing path. Do not reconstruct requirements from memory.

## Approved design foundation

- **Deep Navy Gold** is the approved shared light-theme system
  (PS-BRAND-NAV-002, 2026-07-17), replacing Iris Foundry and the earlier
  Foundation C indigo. One authoritative navy + marigold system applied
  consistently across every room.
- Newsreader is for cinematic/editorial headings.
- Inter is for navigation, controls, forms, metadata, and product content.
- Light-first, cinematic, premium glass UI.
- Cloud White canvas `#F6F7FA`, surface `#FFFFFF`
- Ink Navy text `#141A28`
- Primary Navy `#203767` (strong `#132447`) — primary actions, headings, active/selected
- Marigold `#B87900` (text-safe `#8A5A00`, soft `#F4E4B4`) — evidence chips, progress, gold highlights
- Success Teal `#1E725F`
- Pink, rose, magenta, coral, and purple/iris are not semantic UI accents.
- Use generous vertical spacing and progressive disclosure. Do not force the experience above the fold.
- One dominant product object per opening viewport.
- Never use the retired résumé example. Never use the MICAP example in redesigned résumé fixtures or visible copy.

## Multi-user and trust rules

- Components must work for students, early-career users, career changers, freelancers, mid-career users, and senior users.
- Never hardcode Pete's employers, dates, role count, metrics, education, or skills into reusable components.
- Every profile-owned record must preserve tenant ownership.
- Default new Board content and voice-created drafts to private.
- AI output is a proposal, not an automatic edit.
- Voice flow is transcript → structured proposal → source/visibility review → explicit approval → save. Publishing is a separate explicit action.
- Never imply production privacy, matching, verification, or AI behavior unless the backend enforces it.

## Living Résumé direction — PS-FEAT-001

- The Living Résumé Ledger appears first.
- Its chronological timeline is integrated into the résumé and acts as its navigation and structural spine.
- Selecting a timeline chapter updates detail inside the same dominant résumé frame.
- The Career Constellation materializes below the Ledger during vertical scroll.
- Skills stay compact and reveal only two or three strongest approved proof points.
- Ledger and Constellation render from the same structured data.
- Keep a traditional ATS-friendly PDF/download path.
- Build with generic data/view models and multiple fixture profiles.

## Slate Board direction

- The whiteboard remains the dominant product experience.
- Preserve its playful, hand-placed quality; do not turn it into a conventional dashboard or card grid.
- Four primary scrollable sections for the first implementation:
  - Short Term
  - Projects
  - Long Term
  - Work
- Sticky notes are the primary board objects.
- Add/Edit supports:
  - To Do, Short Term, Long Term, Project, Work, or Custom
  - sticky-note color
  - cursive or standard handwriting
  - dates
  - privacy/audience
- Keep visible controls concise:
  - Add to Board
  - AI Help
  - Connections
  - quiet More/Board Settings
- Item controls appear contextually, not permanently.
- First interaction fixture: “Study for the PMP certification.”
- Add-to-Board states:
  1. Capture
  2. Details and privacy
  3. Note added
  4. AI guidance
  5. People matching
- Similar-user matching is opt-in and visibility-aware. Never auto-connect users.
- AI may propose milestones, questions, reminders, websites, and videos, but does not save automatically.
- Supporting experiences continue vertically below the opening board. Do not pack everything into one screen.
- PS-EXP-002 Focus Stage remains separate, optional, feature-flagged, and off by default. It must never replace the Board.

## Navigation

Do not add another permanent navigation layer inside Slate Board. Global site navigation, public/member Slate navigation, and contextual Board controls must remain distinct. Do not finalize or replace production navigation without an approved route map.

## Safe implementation workflow

- The user grants standing authorization for normal project work: creating task branches, committing, pushing task branches to Azure, creating and completing Azure pull requests, configuring Azure DevOps, deploying through Azure Pipelines, and verifying production behavior. This is not authorization to push directly to `main`, rewrite shared history, or bypass `docs/AI_WORKFLOW.md`.
- Azure DevOps is the source of truth. The remote is named `origin`. GitHub is the `github` mirror and must not deploy the application.
- Preserve current pages and behavior where practical, but make the requested changes and resolve implementation blockers autonomously.
- Prefer reviewable commits and report material changes, but do not treat a dirty worktree or an ambiguous base as an automatic stop condition; inspect it, protect unrelated work, and proceed with the safest reasonable path.
- Do not perform database migrations or add production dependencies without explaining the reason and impact first.
- **Credentials are off-limits:** never request, read, expose, copy, store, commit, rotate, or transmit the user's API keys, passwords, tokens, publish profiles, certificates, or other secrets. Use already-configured secure Azure/Azure DevOps service connections when available; otherwise ask the user to complete the credential-only step themselves.

## Quality requirements

- WCAG 2.2 AA target.
- Keyboard access, visible focus, 200% zoom, high contrast, and reduced motion.
- Slate Board requires an accessible structured/list alternative.
- Mobile uses readable document flow; never shrink a desktop visualization until it is unreadable.
- Prefer transforms and opacity for motion.
- Run the existing test/lint/format commands discovered in the repository.
- Add focused tests for new routes, rendering states, and interactions.
- Capture desktop and mobile screenshots for review.
- Report changed files, commits, commands run, failures, assumptions, and remaining work.

## Communication

Explain architecture and tradeoffs in plain English. Separate:
- what is implemented,
- what is fixture-only,
- what requires backend/schema work,
- what is intentionally deferred.
