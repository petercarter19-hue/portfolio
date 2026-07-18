# PeerSlate — Active Initiatives and Lane Assignments

_Updated 2026-07-18 by PS-BACKEND-NEXT-GATE-MANAGER-001._

## Operating model

**ChatGPT Work is the PeerSlate manager.** It owns package sequencing, governance truth, lane boundaries, handoff review, merge readiness, and release verification. Product implementation stays with one writer per branch.

| Lane | Writer | Active package | Reserved domain | Must not touch |
|---|---|---|---|---|
| Governance and orchestration | ChatGPT Work | PS-BACKEND-NEXT-GATE-MANAGER-001 | `docs/governance/*`, initiative controls, governance guardrail tests | product routes, migrations, public theme |
| Backend convergence | ChatGPT Codex | PS-PLACEMENT-001 | private confirmed-Moment placement references, migration, services, backend tests | public résumé/Studio templates, downstream surface integration, theme, global nav, auth rewrite |
| Public experience | Claude Code | PS-INTERVIEW-PUBLIC-GATE-001 | public Interview Studio design package; implementation only after manager approval | auth, database, Capture/Moment/Placement, owner routes, global theme/nav |

## Current start gate

PS-PLACEMENT-001 may start only after PS-BACKEND-NEXT-GATE-MANAGER-001 is squash-merged and its Azure pipeline is green. Codex must fetch, branch from that exact current `origin/main`, and record the full base SHA. The separate Interview Studio design lane may continue in parallel because it shares no writable files.

### PS-PLACEMENT-001 — prepared for ChatGPT Codex

- Branch when accepted: `work/2026-07-18-placement-001` (or the actual start date).
- Source package: `docs/initiatives/PS-PLACEMENT-001/README.md`.
- Outcome: explicit owner action creates a private, lifecycle-aware reference from one exact confirmed Moment version to one existing owner-owned private/unpublished Slate destination.
- Exit gate: migration up/down evidence, two-owner negative authorization, exact confirmed-version and destination pinning, concurrent duplicate/idempotency proof, no authoritative-text copy, no access/publication/audience mutation, focused and regression tests green, completion report reviewed.

### PS-INTERVIEW-PUBLIC-GATE-001 — Claude Code design lane

- Source package: `docs/initiatives/PS-INTERVIEW-PUBLIC-GATE-001/README.md`.
- Gate A decision: owner-approved on 2026-07-18. Preserve interactive public practice under Approach A.
- Current action: Fable design only under the package's files `05` and `06`; no code until ChatGPT Work reviews the returned design package and expressly authorizes implementation.
- Outcome: an honest public practice experience with clear public-profile grounding, browser-local state, media behavior, and a defined-but-not-faked future `/app/interview-studio` owner boundary.

## Sequenced after Placement

1. **Next owner decision:** choose PS-CAPTURE-MEDIA-001/PS-VOICE-001 or owner Home/viewer-mode work after Placement is verified. Do not infer authorization before manager review.
2. **Downstream consumers:** Story, Work, Project, résumé, Studio, Journal, Feed, sharing, and public projection integrations each require their own later package. PS-PLACEMENT-001 creates the safe reference contract only.

## Held

- **PS-JOURNAL-001:** Journal UI remains on hold by explicit owner decision.

## Shared rules

- Fetch `origin`; never work directly on `main`.
- One short-lived `work/YYYY-MM-DD-task-name` branch and one active writer per package.
- Handoff requires the branch name and exact full commit SHA.
- Merge through an Azure pull request with squash; delete the task branch afterward.
- Close with `docs/templates/OWNER_TECHNICAL_COMPLETION_REPORT.md`.
- Do not duplicate Capture or Moment text into destinations, introduce a second résumé dataset, rewrite authentication, start Journal UI, or claim private/public behavior the backend does not enforce.
