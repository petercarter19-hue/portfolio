# PeerSlate - Active Initiatives and Lane Assignments

_Updated 2026-07-19 after the accepted Voice release and the Interview Studio
Image 5 5A-light/5C-dark owner decision._

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
| Capture Media manager | Claude Co-Work | PS-CAPTURE-MEDIA-001 planning | requirements, architecture, slice decomposition, writer allocation, evidence gates | implementation claims, Voice rebuild, Journal, publication, shared runtime files before reservation |
| Public experience review | Codex Gate 2.4 review session -> Claude Co-Work designated manager -> Claude Code feasibility/implementation after approval | PS-INTERVIEW-PUBLIC-GATE-001 | complete Image 5 Concept A light / Concept C dark design review; implementation only after all gates | auth, database, Capture/Moment/Placement, owner routes, global theme/nav |

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
- The real Studio is upstream of the homepage walkthrough. After design
  approval, Claude Code records the real Studio implementation architecture,
  implements/self-reviews it on a fresh branch, and returns focused visual and
  technical evidence for acceptance. Azure release and live verification of the
  real Studio must pass before the demo branch resumes.
- Homepage demo checkpoint `work/2026-07-19-home-interview-demo-001` at observed
  clean pushed SHA `358e7eea304a2b4d4008031ea8f51c523380ee4f` is a parked
  interaction prototype. It is not accepted, merged, deployed, or live. Preserve
  its modal/accessibility/static-demo shell, then converge it on the exact
  released 5A/5C Studio in a separate branch closeout. Do not release its stale
  paper-light dark treatment or Voice-first framing.
- Outcome: an honest public practice experience with clear public-profile grounding, browser-local state, media behavior, and a defined-but-not-faked future `/app/interview-studio` owner boundary.

### PS-CAPTURE-MEDIA-001 - Claude Co-Work manager-planning lane

- Source package: `docs/initiatives/PS-CAPTURE-MEDIA-001/README.md`.
- Current action: inventory the released Voice/private-media foundation; define
  separate photo, video, and document vertical slices; select the first slice;
  allocate one implementation writer/branch; and return requirements,
  architecture, privacy/lifecycle, accessibility, infrastructure, test,
  rollout, and rollback gates.
- No authoritative remote Capture Media implementation branch was observed at
  activation. Planning may proceed, but implementation, deployment, and live
  status remain false until exact branch/PR/pipeline/production evidence exists.
- The released PS-VOICE-001 foundation remains separate and must not be
  reimplemented by Capture Media.

## Later backend decisions

Owner Home/viewer mode, photo/video/document Capture, and each Story/Work/Project/resume/Studio/Journal/Feed/sharing/public-projection consumer remain separate later packages. PS-VOICE-001 does not authorize them.

`PS-STORY-COMPOSER-001` is now reserved as a planned future cross-lane package.
It will add member-controlled move, resize, layering, responsive layout drafts,
and explicit Story publication under
`docs/governance/OWNER_STORY_COMPOSITION_STANDARD.md`. It is not active, has no
writer or implementation branch, and must not interrupt Voice or Interview.

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
- Manager-to-manager transfer requires a durable package report naming the
  current gate, exact branch/SHA, evidence, shared-file reservation, unresolved
  issues, and single next action. Chat history alone is not a handoff.
- Do not duplicate Capture or Moment text into destinations, introduce a second resume dataset, rewrite authentication, start Journal UI, or claim private/public behavior the backend does not enforce.
