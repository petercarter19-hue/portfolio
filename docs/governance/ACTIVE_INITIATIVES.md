# PeerSlate - Active Initiatives and Lane Assignments

_Updated 2026-07-18 by PS-STORY-COMPOSER-DIRECTION-001._

## Operating model

**ChatGPT Work is the PeerSlate manager.** It owns package sequencing, governance truth, lane boundaries, handoff review, merge readiness, and release verification. Product implementation stays with one writer per branch.

| Lane | Writer | Active package | Reserved domain | Must not touch |
|---|---|---|---|---|
| Governance and orchestration | ChatGPT Work | Visual-integrity governance released; monitoring Voice and Interview gates | Current authority/state, lane sequencing, handoff review, release verification | product routes, migrations, active Voice/Interview implementation files |
| Backend convergence | ChatGPT Codex | PS-VOICE-001 active | protected Capture voice routes/UI, voice services, media/transcription schema, infrastructure automation, focused tests | public resume/Studio, downstream Moment/Placement consumers, Journal, global theme/nav, auth rewrite |
| Public experience | ChatGPT Pro visual direction, then Claude Code feasibility/implementation after approval | PS-INTERVIEW-PUBLIC-GATE-001 | Direction A Gate 2.4 design package; implementation only after complete visual gate and approval | auth, database, Capture/Moment/Placement, owner routes, global theme/nav |

## Current active gate

PS-VOICE-CAPTURE-MANAGER-001 is released through PR 70 / pipeline 97. ChatGPT
Codex is actively implementing `PS-VOICE-001` in its own worktree. The manager
must not touch that branch and waits for a clean pushed branch, exact full SHA,
completion report, and explicit writer relinquishment before review.

### PS-VOICE-001 - ChatGPT Codex backend lane

- Source package: `docs/initiatives/PS-VOICE-001/README.md` and its architecture/security/infrastructure/test/implementation contracts.
- Outcome: short authenticated recording -> private original audio -> server-side transcription -> member review/correction -> explicit private voice Capture.
- Text Capture remains the fallback. No Moment, Placement, Journal, resume, Interview Studio, share, or publication is created automatically.
- Codex writes and proves code, SQL, and idempotent infrastructure automation in isolation, then returns the exact branch/SHA. ChatGPT Work owns production resources, migration, PR, deploy, and live validation.
- At manager review, the protected UI must also pass the owner visual addendum:
  match or exceed the homepage Voice walkthrough, keep Speak and Type first
  class, and provide full desktop/mobile/accessibility/failure comparison evidence.

### PS-INTERVIEW-PUBLIC-GATE-001 - Claude Code design lane

- Source package: `docs/initiatives/PS-INTERVIEW-PUBLIC-GATE-001/README.md`.
- Gate A decision: owner-approved on 2026-07-18. Preserve interactive public practice under Approach A.
- Current action: Direction A, Editorial Studio Ledger, is selected. ChatGPT Pro
  must complete the nine-screen Gate 2.4 responsive/accessibility design set and
  a separately scoped homepage walkthrough design. Claude Code then performs
  feasibility review. No code until Pete and ChatGPT Work approve the final
  design baseline and expressly authorize implementation.
- Outcome: an honest public practice experience with clear public-profile grounding, browser-local state, media behavior, and a defined-but-not-faked future `/app/interview-studio` owner boundary.

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
- Handoff requires the branch name and exact full commit SHA.
- Merge through an Azure pull request with squash; delete the task branch afterward.
- Close with `docs/templates/OWNER_TECHNICAL_COMPLETION_REPORT.md`.
- Follow `docs/governance/OWNER_VISUAL_INTEGRITY_STANDARD.md`; material
  user-facing work requires a named visual authority, parity evidence, and Pete
  plus ChatGPT Work visual acceptance.
- Do not duplicate Capture or Moment text into destinations, introduce a second resume dataset, rewrite authentication, start Journal UI, or claim private/public behavior the backend does not enforce.
