# PeerSlate - Active Initiatives and Lane Assignments

_Updated 2026-07-18 by PS-VOICE-CAPTURE-MANAGER-001._

## Operating model

**ChatGPT Work is the PeerSlate manager.** It owns package sequencing, governance truth, lane boundaries, handoff review, merge readiness, and release verification. Product implementation stays with one writer per branch.

| Lane | Writer | Active package | Reserved domain | Must not touch |
|---|---|---|---|---|
| Governance and orchestration | ChatGPT Work | PS-VOICE-CAPTURE-MANAGER-001 | `docs/governance/*`, initiative controls, governance guardrail tests | product routes, migrations, public theme |
| Backend convergence | ChatGPT Codex | PS-VOICE-001 after manager merge/pipeline | protected Capture voice routes/UI, voice services, media/transcription schema, infrastructure automation, focused tests | public resume/Studio, downstream Moment/Placement consumers, Journal, global theme/nav, auth rewrite |
| Public experience | ChatGPT Pro visual direction, then Claude Code feasibility/implementation after approval | PS-INTERVIEW-PUBLIC-GATE-001 | current-public Interview Studio design package; implementation only after manager and owner approval | auth, database, Capture/Moment/Placement, owner routes, global theme/nav |

## Current start gate

Pete approved private Voice Capture as the next backend package. ChatGPT Codex starts `PS-VOICE-001` only after PS-VOICE-CAPTURE-MANAGER-001 is squash-merged and the matching Azure pipeline is green, using a fresh branch from that current `origin/main`.

### PS-VOICE-001 - ChatGPT Codex backend lane

- Source package: `docs/initiatives/PS-VOICE-001/README.md` and its architecture/security/infrastructure/test/implementation contracts.
- Outcome: short authenticated recording -> private original audio -> server-side transcription -> member review/correction -> explicit private voice Capture.
- Text Capture remains the fallback. No Moment, Placement, Journal, resume, Interview Studio, share, or publication is created automatically.
- Codex writes and proves code, SQL, and idempotent infrastructure automation in isolation, then returns the exact branch/SHA. ChatGPT Work owns production resources, migration, PR, deploy, and live validation.

### PS-INTERVIEW-PUBLIC-GATE-001 - Claude Code design lane

- Source package: `docs/initiatives/PS-INTERVIEW-PUBLIC-GATE-001/README.md`.
- Gate A decision: owner-approved on 2026-07-18. Preserve interactive public practice under Approach A.
- Current action: ChatGPT Pro supplies the visual-art-direction revision while preserving Claude/Fable's functional blueprint. Claude Code then performs feasibility review. No code until Pete and ChatGPT Work approve the final design baseline and expressly authorize implementation.
- Outcome: an honest public practice experience with clear public-profile grounding, browser-local state, media behavior, and a defined-but-not-faked future `/app/interview-studio` owner boundary.

## Later backend decisions

Owner Home/viewer mode, photo/video/document Capture, and each Story/Work/Project/resume/Studio/Journal/Feed/sharing/public-projection consumer remain separate later packages. PS-VOICE-001 does not authorize them.

## Held

- **PS-JOURNAL-001:** Journal UI remains on hold by explicit owner decision.

## Shared rules

- Fetch `origin`; never work directly on `main`.
- One short-lived `work/YYYY-MM-DD-task-name` branch and one active writer per package.
- Handoff requires the branch name and exact full commit SHA.
- Merge through an Azure pull request with squash; delete the task branch afterward.
- Close with `docs/templates/OWNER_TECHNICAL_COMPLETION_REPORT.md`.
- Do not duplicate Capture or Moment text into destinations, introduce a second resume dataset, rewrite authentication, start Journal UI, or claim private/public behavior the backend does not enforce.
