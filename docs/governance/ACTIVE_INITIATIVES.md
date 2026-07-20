# PeerSlate - Active Initiatives and Lane Assignments

_Updated 2026-07-20 after the flag-off Photo experience release, default-off
Owner Home backend release, and owner-delegated manager acceptance of Claude
Code's exact 5A-light/5C-dark Interview implementation._

## Operating model

The manager is a package-designated role. A ChatGPT Work/Codex manager session
or Claude Co-Work has the same authority when named: package sequencing,
governance truth, shared-file boundaries, visual authority, exception
escalation, and final manager acceptance. Each assigned writer self-manages its
own branch through implementation, complete-diff review, tests, evidence, PR
readiness, and post-acceptance release/closeout.

Each package has one designated session manager. Parallel managers may
coordinate different packages, but they may not edit the same branch or reserve
the same shared governance files. Claude Co-Work management is distinct from
Claude Code implementation.

| Lane | Writer | Active package | Reserved domain | Must not touch |
|---|---|---|---|---|
| Governance and orchestration | ChatGPT Work/Codex owner-delegated manager | Interview release, Capture Media enablement, Owner Home sequencing | Current authority/state, lane sequencing, final acceptance, Azure closeout | editing Claude's active Interview branch; combining product lanes |
| Capture Media enablement | Unassigned | PS-CAPTURE-MEDIA-001 | later signed-in Photo lifecycle, two-owner, homepage-parity, and enablement gates | enabling Photo now; rebuilding Voice; blending Owner Home work |
| Public Interview implementation | Claude Code sole writer | PS-INTERVIEW-PUBLIC-GATE-001 | merge preparation, one report correction, test reruns, Azure release and closeout for exact accepted SHA | auth, database, Capture/Moment/Placement, owner routes, global theme/nav, Owner Home |
| Owner Home frontend | Unassigned; Claude Code preferred when separately assigned | PS-HOME-FRONTEND-001 ready but not active | exact accepted dark cinematic shell from post-backend main | Interview branch, broader viewer modes, Photo enablement, backend-contract expansion |

## Current active gate

PS-VOICE-001 is no longer an active gate. Pete and ChatGPT Work accepted the
corrected implementation after Claude Code relinquished exact tip
`e32b31d7c351ac2f8601a4467bcd1c9450f52c3b`. Azure PR 80 squash-merged the
package at `864a79d1bc1fc61e62f2d2a544dd54a01ebdcb82`; pipeline 113 passed Build
and Deploy. Preserve the original and visual-correction worktrees as historical
references; do not reuse them for later work. A future Voice change requires a
new package and branch.

### PS-INTERVIEW-PUBLIC-GATE-001 - manager accepted / Claude Code release lane

- Source package: `docs/initiatives/PS-INTERVIEW-PUBLIC-GATE-001/README.md`.
- Gate A decision: owner-approved on 2026-07-18. Preserve interactive public practice under Approach A.
- Owner visual authority updated 2026-07-19: exact Image 5 Concept A Editorial
  Studio Ledger controls default/light and Concept C Cinematic Studio controls
  optional dark. Both themes share one public route, DOM, state machine,
  functionality, truth, responsive behavior, and accessibility model.
- Pete delegated the current ChatGPT Work/Codex manager to review and approve
  the implementation gates needed for the cross-computer release handoff. The
  exact Claude Code branch
  `work/2026-07-19-interview-public-gate-001` at
  `39bc9a3f890ec8020eb84c4e3e416db6cd6912d2` passed manager visual/product
  review, 70 focused tests, 518 full-suite tests with one skip, and diff checks.
- Claude Code remains the sole active writer. On the Mac it must merge current
  `origin/main` without rebasing, correct the one stale Bible/Roadmap sentence,
  rerun evidence, push the exact corrected tip, and complete the Azure squash
  PR, pipeline, live verification, completion report, and governance closeout.
- The real Studio remains upstream of the homepage walkthrough. Its Azure
  release and live verification must pass before a fresh homepage-parity
  convergence branch starts.
- Pete accepted the current fixed illustrative walkthrough for its present
  purpose. Claude's exact source tip
  `90d035a25344c850e6ed732c1efb6e4d0a240787` squash-merged through Azure PR 86
  at `a98cced519a1f853ad9f4462fd438efa67d6f260`; automatic pipeline 122
  (`20260719.30`) passed Build and Deploy. Automatic pipeline 123 then released
  descendant main `6cb49f135cc3a2749dd4539f8261d176b43dad9a` with the demo-owned
  paths unchanged. Manual pipeline 124 was an additional successful run, not
  evidence of a disabled CI trigger. Live `/` and both demo assets return 200,
  and manager review passed the four-state desktop/390px illustrative flow.
- This release closes `PS-HOME-INTERVIEW-DEMO-001` as an honest demonstration,
  not as final homepage parity. A fresh downstream branch must later replace
  the Voice-default emphasis and paper-light dark modal with a mapped projection
  of the exact accepted and live 5A/5C Studio. Preserve the historical demo
  worktree; do not reuse or delete it during the active Studio gate.
- The convergence governance is authoritative on `origin/main`: Azure PR 83
  squash-merged at `cee015f6291fe5460a6a5d5795c445bb6b25c6f9`, and
  pipeline 117 passed Build and Deploy. This release records sequencing only;
  it does not make the new Studio design or homepage demo implemented or live.
- Outcome: an honest public practice experience with clear public-profile grounding, browser-local state, media behavior, and a defined-but-not-faked future `/app/interview-studio` owner boundary.

### PS-CAPTURE-MEDIA-001 - released flag-off / enablement gates unassigned

- Source package: `docs/initiatives/PS-CAPTURE-MEDIA-001/README.md`.
- Photo-first planning and the default-off backend are complete. Azure PR 95
  squash-merged at `e4863a57f9642731073f232a973508615e116d72`; pipeline 139
  passed. Closeout PR 96 squash-merged at
  `67b7053fcf9ba8bf37c1bbdc5aa2d275e31dc1b7`; pipeline 140 passed. The Photo
  flag remains off and no new member-facing capability is live.
- The accepted Photo 1 experience source
  `a19a5034aa7f3b9d355f8862aa98a34eb9f3e5f6` squash-merged through Azure PR 98
  at `e5912c85d95dddbaed9c565d1e599efe2c8dd0b6`; automatic pipeline 143 passed
  Build and Deploy. The flag remains off and no new member-facing capability is
  live.
- Current action: do not enable Photo. A separately assigned package must prove
  the real signed-in Azure lifecycle, two-owner denial, production visuals, and
  `PS-HOME-CAPTURE-PHOTO-PARITY-001` before an enablement decision.
- The released PS-VOICE-001 foundation remains separate and must not be
  reimplemented by Capture Media.

### PS-HOME-BACKEND-001 - released default-off / frontend unblocked

- Source package: `docs/initiatives/PS-HOME-BACKEND-001/README.md`.
- Accepted architecture and U1–U6 decisions:
  `docs/initiatives/PS-OWNER-HOME-VIEWER-GATE-001/11_MANAGER_ACCEPTANCE_AND_ACTIVATION.md`.
- ChatGPT Codex completed the self-managed backend at source
  `efd19d820986a529d48e2fcf660655b9f4dfc492`. Azure PR 99 squash-merged it at
  `2db2ca5c93fa221f7092b54ebc17f2068584c07d`; automatic pipeline 145 passed
  Build and Deploy. Production SQL migration/verifier evidence passed through
  the configured passwordless identity.
- Scope is only the default-off `PEERSLATE_OWNER_HOME_ENABLED` config, bounded
  owner read procedure/service/serializer, flag-gated
  `GET /api/v1/owner/home`, exact migration/rollback/verification, and required
  tests/evidence. The backend package does not edit `auth_routes.py`, render an
  Owner Home template, or change `/app`.
- First review kinds are fixed: failed Voice, pending Moment proposal, then
  ready Voice; oldest actionable item first within kind, then opaque key.
- `PEERSLATE_OWNER_HOME_ENABLED` remains false, `/app` is unchanged, and the
  new API returns neutral 404. The backend is deployed; Owner Home remains
  intentionally not member-visible.
- `PS-HOME-FRONTEND-001` is unblocked but not assigned. It must start on a fresh
  branch from then-current `origin/main`, own the controlled flag-on `/app`
  switch and exact dark cinematic shell, and pass its own visual/product gate.
  It must not be blended into Claude's active Interview branch.

## Later backend decisions

The finite Owner Home backend is released. Owner Home frontend is ready for a
separate assignment after the Interview writer lane is safely released, unless
a different writer and isolated worktree are explicitly assigned. Broader viewer modes,
photo/video/document Capture, and each Story/Work/Project/resume/Studio/Journal/
Feed/sharing/public-projection consumer remain separate later packages.
PS-VOICE-001 does not authorize them.

`PS-STORY-COMPOSER-001` is now reserved as a planned future cross-lane package.
It will add member-controlled move, resize, layering, responsive layout drafts,
and explicit Story publication under
`docs/governance/OWNER_STORY_COMPOSITION_STANDARD.md`. It is not active, has no
writer or implementation branch, and must not interrupt Voice or Interview.

### PS-PROJECTS-001 - planned Phase 10 expansion

- Source package: `docs/initiatives/PS-PROJECTS-001/README.md`.
- Product direction: a private-first, member-owned Project Workspace connects a
  meaningful endeavor to exact governed records and relationships without
  copying canonical facts. Purpose- and audience-specific Project Projections
  are separate later objects with explicit draft, preview, publication, and
  revocation boundaries.
- Work remains the broader roles-and-contributions domain. Slate Board Project
  notes remain planning objects and are not canonical Projects. Historical Pete
  fixtures and redirects do not define the authenticated product model.
- The first eventual implementation slice is owner-only Project creation and
  lifecycle, Slate entity registration, reuse of exact-version Moment
  Placements, a Project Ledger, and two-owner isolation. It excludes public
  projection, collaboration, task management, homepage work, and route revival.
- Entry requires Project/Work/Slate Board boundary validation, one selected
  production-intent Project Workspace authority, joint product/architecture
  baseline, named manager and writer, fresh branch, reserved files, and explicit
  Pete/designated-manager approval.
- No manager, writer, implementation branch, start date, schema migration,
  accepted product mockup, deployment, or live claim exists. This package must
  not interrupt active Interview Studio or Capture Media gates.

### PS-ASK-PETE-AI-001 - planned Phase 11 discovery

- Source package: `docs/initiatives/PS-ASK-PETE-AI-001/README.md`.
- Working product name: **Ask Pete AI**. This is not "PAI." The naming and
  permission relationship to reusable Ask [Name] AI and private Owner AI is a
  future discovery decision; no current live label changes.
- Current production remains the public, typed, approved-source Ask Pete AI
  assistant. Voice, private owner-history retrieval, document upload,
  screenshot/OCR processing, saved targets, and Qualification Alignment are not
  implemented, deployed, or live.
- Planned inputs to explore include Type, Speak, PDF/DOCX/TXT, and one or more
  PNG/JPEG screenshots such as job postings. The member must review extracted
  text and source spans before consequential analysis.
- Roadmap placement is Phase 11, Next Chapter and Qualification Alignment. The
  first action is the owner discovery agenda, followed by complete experience,
  visual-authority, architecture, privacy, AI-safety, and traceability gates.
- No designated discovery manager, implementation writer, product branch, or
  start date is assigned. This package must not interrupt the active Interview
  Studio or Capture Media gates.
- Any homepage section that presents or links Ask Pete AI is subject to the
  cross-product homepage projection parity contract before future product
  implementation can close.

## Held

- **PS-JOURNAL-001:** Journal UI remains on hold by explicit owner decision.

## Shared rules

- Fetch `origin`; never work directly on `main`.
- One short-lived `work/YYYY-MM-DD-task-name` branch and one active writer per package.
- A handoff requires the branch name and exact full commit SHA when a different
  writer continues the branch. A self-managed writer may retain ownership
  through post-acceptance release and closeout.
- Every writer performs a distinct complete-diff self-review and reports
  `Pass`, `Conditional`, or `Fail` with exact evidence. Failed or conflicting
  evidence may not be represented as passed.
- Merge through an Azure pull request with squash; delete the task branch afterward.
- Close with `docs/templates/OWNER_TECHNICAL_COMPLETION_REPORT.md`.
- Follow `docs/governance/OWNER_VISUAL_INTEGRITY_STANDARD.md`; material
  user-facing work requires a named visual authority, parity evidence, and Pete
  plus designated-session-manager visual acceptance.
- Every user-facing package records a homepage-impact assessment. If `/`
  presents, demonstrates, or links that product, material function or visual
  changes require a same-wave homepage update or an exact downstream parity
  package; the real product remains upstream authority and parity stays open
  until the public projection is current and accepted.
- Manager-to-manager transfer requires a durable package report naming the
  current gate, exact branch/SHA, evidence, shared-file reservation, unresolved
  issues, and single next action. Chat history alone is not a handoff.
- Do not duplicate Capture or Moment text into destinations, introduce a second resume dataset, rewrite authentication, start Journal UI, or claim private/public behavior the backend does not enforce.
