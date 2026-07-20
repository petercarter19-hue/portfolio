# PeerSlate - Active Initiatives and Lane Assignments

_Updated 2026-07-19 after the accepted Voice release, the Interview Studio
Image 5 5A-light/5C-dark owner decision, the accepted live pre-convergence
homepage walkthrough, planned Projects and Ask Pete AI expansion, and the
cross-product homepage parity decision, plus the accepted finite Owner Home
architecture and activated backend slice._

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
| Governance and orchestration | Package-designated ChatGPT Work/Codex or Claude Co-Work manager | Portable management; Interview and Capture Media gates | Current authority/state, lane sequencing, shared-file reservations, final acceptance | routine duplicate technical audits; active product implementation files |
| Capture Media manager | Claude Co-Work | PS-CAPTURE-MEDIA-001 Photo visual gate after released flag-off backend | Photo design/experience sequencing, evidence gates | Voice rebuild, Journal, publication, Home files without a new reservation |
| Public experience review | Codex Gate 2.4 review session -> Claude Co-Work designated manager -> Claude Code feasibility/implementation after approval | PS-INTERVIEW-PUBLIC-GATE-001 | complete Image 5 Concept A light / Concept C dark design review; implementation only after all gates | auth, database, Capture/Moment/Placement, owner routes, global theme/nav |
| Owner Home backend | ChatGPT Codex self-managed writer; ChatGPT Work/Codex designated manager; cleared to start | PS-HOME-BACKEND-001 | default-off finite owner read procedure/service/JSON API, tests, SQL evidence | `/app` HTML, templates/CSS/JS, viewer modes, public/homepage surfaces, Capture/Moment/Voice internals |

## Current active gate

PS-VOICE-001 is no longer an active gate. Pete and ChatGPT Work accepted the
corrected implementation after Claude Code relinquished exact tip
`e32b31d7c351ac2f8601a4467bcd1c9450f52c3b`. Azure PR 80 squash-merged the
package at `864a79d1bc1fc61e62f2d2a544dd54a01ebdcb82`; pipeline 113 passed Build
and Deploy. Preserve the original and visual-correction worktrees as historical
references; do not reuse them for later work. A future Voice change requires a
new package and branch.

### PS-INTERVIEW-PUBLIC-GATE-001 - Codex Gate 2.4 review / Claude Co-Work manager lane

- Source package: `docs/initiatives/PS-INTERVIEW-PUBLIC-GATE-001/README.md`.
- Gate A decision: owner-approved on 2026-07-18. Preserve interactive public practice under Approach A.
- Owner visual authority updated 2026-07-19: exact Image 5 Concept A Editorial
  Studio Ledger controls default/light and Concept C Cinematic Studio controls
  optional dark. Both themes share one public route, DOM, state machine,
  functionality, truth, responsive behavior, and accessibility model.
- Current action: Pete may start a new Codex manager session, upload the
  complete dual-theme Gate 2.4 package, and
  let that session create a clean review branch from current `origin/main`.
  The session reviews all nine states in both themes, responsive/accessibility
  evidence, theme persistence/no-state-loss, the separately scoped homepage
  walkthrough, truth/accessibility, and implementation mapping; it does not
  write product code. It returns its exact branch/SHA and
  `Pass`/`Conditional`/`Fail` report to Claude Co-Work.
- Claude Co-Work receives the durable review as designated manager and sends
  the accepted package to Claude Code for feasibility. No implementation branch
  until feasibility and Pete/designated-manager visual approval pass.
- The real Studio remains upstream of the homepage walkthrough. After design
  approval, Claude Code records the real Studio implementation architecture,
  implements/self-reviews it on a fresh branch, and returns focused visual and
  technical evidence for acceptance. Azure release and live verification of the
  real Studio must pass before the separate homepage-parity convergence starts.
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

### PS-CAPTURE-MEDIA-001 - Claude Co-Work manager-planning lane

- Source package: `docs/initiatives/PS-CAPTURE-MEDIA-001/README.md`.
- Photo-first planning and the default-off backend are complete. Azure PR 95
  squash-merged at `e4863a57f9642731073f232a973508615e116d72`; pipeline 139
  passed. Closeout PR 96 squash-merged at
  `67b7053fcf9ba8bf37c1bbdc5aa2d275e31dc1b7`; pipeline 140 passed. The Photo
  flag remains off and no new member-facing capability is live.
- Current action: complete and accept `PS-CAPTURE-PHOTO-DESIGN-001`, then
  assign the separate runtime experience package. Photo's Home intersections
  are closed; future Photo work must reserve its own files without reclaiming
  the active Home backend reservations.
- The released PS-VOICE-001 foundation remains separate and must not be
  reimplemented by Capture Media.

### PS-HOME-BACKEND-001 - active finite Owner Home backend lane

- Source package: `docs/initiatives/PS-HOME-BACKEND-001/README.md`.
- Accepted architecture and U1–U6 decisions:
  `docs/initiatives/PS-OWNER-HOME-VIEWER-GATE-001/11_MANAGER_ACCEPTANCE_AND_ACTIVATION.md`.
- Assigned writer: ChatGPT Codex on one fresh
  `work/YYYY-MM-DD-home-backend-001` branch; designated manager: ChatGPT
  Work/Codex manager session. Capture Photo PR 95 and closeout PR 96 are merged,
  pipelines 139 and 140 passed, and both overlapping file reservations are
  closed. The assignment is active and cleared to start from `origin/main`
  after this manager correction merges.
- Scope is only the default-off `PEERSLATE_OWNER_HOME_ENABLED` config, bounded
  owner read procedure/service/serializer, flag-gated
  `GET /api/v1/owner/home`, exact migration/rollback/verification, and required
  tests/evidence. The backend package does not edit `auth_routes.py`, render an
  Owner Home template, or change `/app`.
- First review kinds are fixed: failed Voice, pending Moment proposal, then
  ready Voice; oldest actionable item first within kind, then opaque key.
- `PS-HOME-FRONTEND-001` is sequenced but not active. It starts only from the
  merged backend main, owns the flag-on `/app` switch and exact dark cinematic
  shell, and requires Pete plus manager visual acceptance.
- Owner Home is not implemented, deployed, enabled, or live. Broader viewer,
  preview, insight, connection, sharing, and publication packages remain gated.

## Later backend decisions

The finite Owner Home backend is now active as the isolated package above.
Owner Home frontend is sequenced after it. Broader viewer modes,
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
