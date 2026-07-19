# PeerSlate - Active Initiatives and Lane Assignments

_Updated 2026-07-19 for portable package management, Interview Gate 2.4 review, and Capture Media planning._

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
| Governance and orchestration | Package-designated ChatGPT Work/Codex or Claude Co-Work manager | Portable management; Voice, Interview, and Capture Media gates | Current authority/state, lane sequencing, shared-file reservations, final acceptance | routine duplicate technical audits; active product implementation files |
| Capture Media manager | Claude Co-Work | PS-CAPTURE-MEDIA-001 planning | requirements, architecture, slice decomposition, writer allocation, evidence gates | implementation claims, Voice rebuild, Journal, publication, shared runtime files before reservation |
| Protected front end | Claude Code | PS-VOICE-001 visual-parity correction | protected Voice Capture template/scoped CSS/client/tests/evidence | Voice backend, auth, SQL, infrastructure, public Studio/resume, global theme/nav |
| Public experience review | Codex Gate 2.4 review session -> Claude Co-Work designated manager -> Claude Code feasibility/implementation after approval | PS-INTERVIEW-PUBLIC-GATE-001 | complete Direction A design review; implementation only after all gates | auth, database, Capture/Moment/Placement, owner routes, global theme/nav |

## Current active gate

PS-VOICE-001 is deployed through PR 75 / pipeline 105 and Pete verified that the
signed-in workflow works. Pete then rejected the visual execution as materially
below the approved walkthrough. Claude Code is assigned the corrective
self-managed frontend lane on a new branch from current `origin/main`. Preserve
the original `C:\Users\peter\Documents\portfolio-voice-001` worktree.
The reserved branch is `work/2026-07-19-voice-visual-parity-001`; its observed
checkpoint `0158daf22d26e7c38be494e2b32e6b51fdaca0fb` contains design
instructions only and must synchronize with current `origin/main` before build.

### PS-VOICE-001 - Claude Code protected visual-correction lane

- Source package: `docs/initiatives/PS-VOICE-001/README.md` and its architecture/security/infrastructure/test/implementation contracts.
- Current real outcome: short authenticated recording -> private original audio -> server-side transcription -> member review/correction -> explicit private voice Capture.
- Text Capture remains the fallback. No Moment, Placement, Journal, resume, Interview Studio, share, or publication is created automatically.
- Claude changes only the protected frontend allocation described in
  `06_VISUAL_PARITY_CORRECTION.md`; backend routes, SQL, Blob, Speech, identity,
  and lifecycle behavior remain fixed.
- The design-instructions checkpoint is manager-approved with the binding
  answers in the correction addendum. Claude may implement without another
  pre-build manager audit; final real-product acceptance remains required.
- Claude self-reviews the complete branch, corrects its own issues, runs all
  required evidence, and returns `Pass`, `Conditional`, or `Fail`. Pete and
  the designated session manager then perform a focused real-product acceptance review. After
  acceptance Claude may complete its Azure PR, pipeline, production checks, and
  package closeout.
- The protected UI must match or exceed the homepage/feed Voice walkthrough,
  keep Speak and Type first class, and prove desktop/mobile/accessibility/failure
  parity. Approved future actions remain clearly disabled `Coming later`
  scaffolding; **Save private Capture** is the only live completion action.

### PS-INTERVIEW-PUBLIC-GATE-001 - Codex Gate 2.4 review / Claude Co-Work manager lane

- Source package: `docs/initiatives/PS-INTERVIEW-PUBLIC-GATE-001/README.md`.
- Gate A decision: owner-approved on 2026-07-18. Preserve interactive public practice under Approach A.
- Current action: Direction A, Editorial Studio Ledger, is selected. Pete may
  start a new Codex manager session, upload the complete Gate 2.4 package, and
  let that session create a clean review branch from current `origin/main`.
  The session reviews all nine responsive/accessibility states, the separately
  scoped homepage walkthrough, truth/accessibility, and implementation mapping;
  it does not write product code. It returns its exact branch/SHA and
  `Pass`/`Conditional`/`Fail` report to Claude Co-Work.
- Claude Co-Work receives the durable review as designated manager and sends
  the accepted package to Claude Code for feasibility. No implementation branch
  until feasibility and Pete/designated-manager visual approval pass.
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
- PS-VOICE-001 remains separate and must not be reimplemented by Capture Media.

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
