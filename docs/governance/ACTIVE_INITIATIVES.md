# PeerSlate — Active Initiatives and Lane Assignments

_Updated 2026-07-18 by PS-PLACEMENT-RELEASE-MANAGER-001._

## Operating model

**ChatGPT Work is the PeerSlate manager.** It owns package sequencing, governance truth, lane boundaries, handoff review, merge readiness, and release verification. Product implementation stays with one writer per branch.

| Lane | Writer | Active package | Reserved domain | Must not touch |
|---|---|---|---|---|
| Governance and orchestration | ChatGPT Work | PS-PLACEMENT-RELEASE-MANAGER-001 | `docs/governance/*`, initiative controls, governance guardrail tests | product routes, migrations, public theme |
| Backend convergence | ChatGPT Codex | None; waiting for owner decision | no writable reservation | public résumé/Studio templates, downstream surface integration, theme, global nav, auth rewrite |
| Public experience | ChatGPT Pro visual direction, then Claude Code feasibility/implementation after approval | PS-INTERVIEW-PUBLIC-GATE-001 | current-public Interview Studio design package; implementation only after manager and owner approval | auth, database, Capture/Moment/Placement, owner routes, global theme/nav |

## Current start gate

PS-PLACEMENT-001 is complete and released. ChatGPT Codex must not infer the next backend package. Pete must choose between voice/non-text Capture and owner Home/viewer-mode work; ChatGPT Work will then prepare the controlled package and fresh branch from current `origin/main`.

### PS-INTERVIEW-PUBLIC-GATE-001 — Claude Code design lane

- Source package: `docs/initiatives/PS-INTERVIEW-PUBLIC-GATE-001/README.md`.
- Gate A decision: owner-approved on 2026-07-18. Preserve interactive public practice under Approach A.
- Current action: ChatGPT Pro supplies the visual-art-direction revision while preserving Claude/Fable's functional blueprint. Claude Code then performs feasibility review. No code until Pete and ChatGPT Work approve the final design baseline and expressly authorize implementation.
- Outcome: an honest public practice experience with clear public-profile grounding, browser-local state, media behavior, and a defined-but-not-faked future `/app/interview-studio` owner boundary.

## Next backend decision

1. **Recommended:** PS-CAPTURE-MEDIA-001/PS-VOICE-001, beginning with voice capture into the existing private Capture lifecycle. This directly addresses the owner's requested voice path while preserving transcript → proposal → source/visibility review → explicit approval.
2. **Alternative:** owner Home/viewer-mode work, making the authenticated workspace and private/public viewing boundary more visible before expanding Capture inputs.
3. **Later consumers:** Story, Work, Project, résumé, Studio, Journal, Feed, sharing, and public projection integrations each require their own later package. PS-PLACEMENT-001 created the safe reference contract only.

## Held

- **PS-JOURNAL-001:** Journal UI remains on hold by explicit owner decision.

## Shared rules

- Fetch `origin`; never work directly on `main`.
- One short-lived `work/YYYY-MM-DD-task-name` branch and one active writer per package.
- Handoff requires the branch name and exact full commit SHA.
- Merge through an Azure pull request with squash; delete the task branch afterward.
- Close with `docs/templates/OWNER_TECHNICAL_COMPLETION_REPORT.md`.
- Do not duplicate Capture or Moment text into destinations, introduce a second résumé dataset, rewrite authentication, start Journal UI, or claim private/public behavior the backend does not enforce.
