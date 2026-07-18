# PeerSlate — Active Initiatives and Lane Assignments

_Updated 2026-07-18 by PS-NEXT-WAVE-MANAGER-001._

## Operating model

**ChatGPT Work is the PeerSlate manager.** It owns package sequencing, governance truth, lane boundaries, handoff review, merge readiness, and release verification. Product implementation stays with one writer per branch.

| Lane | Writer | Active package | Reserved domain | Must not touch |
|---|---|---|---|---|
| Governance and orchestration | ChatGPT Work | PS-NEXT-WAVE-MANAGER-001 closeout | `docs/governance/*`, initiative controls, governance guardrail tests | product routes, migrations, public theme |
| Backend convergence | ChatGPT Codex | PS-MOMENT-001 | private Capture-to-Moment services/routes, `dbo.*`, migration, backend tests, minimal protected owner controls | public résumé/Studio templates, theme, global nav, auth rewrite, placement |
| Public experience | Claude Code | PS-INTERVIEW-PUBLIC-GATE-001 | public Interview Studio template/CSS/JS and focused tests | auth, database, Capture/Moment, owner routes, global theme/nav |

## Parallel start gate

The two product packages may start in parallel only after PS-NEXT-WAVE-MANAGER-001 is squash-merged and its Azure pipeline is green. Each writer must fetch, create its own branch from that exact current tip, and record the full base SHA in its first handoff.

### PS-MOMENT-001 — prepared for ChatGPT Codex

- Branch when accepted: `work/2026-07-18-moment-001` (or the actual start date).
- Source package: `docs/initiatives/PS-MOMENT-001/README.md`.
- Outcome: owner-scoped original Capture source → editable private proposal → explicit member confirmation into a source-linked canonical Moment.
- Exit gate: migration up/down evidence, two-owner negative authorization, pinned source-version behavior, no automatic publication/placement, focused and regression tests green, completion report reviewed.

### PS-INTERVIEW-PUBLIC-GATE-001 — prepared for Claude Code

- Branch when accepted: `work/2026-07-18-interview-public-gate-001` (or the actual start date).
- Source package: `docs/initiatives/PS-INTERVIEW-PUBLIC-GATE-001/README.md`.
- Outcome: an honest public demonstration with clear public-profile grounding, browser-local state, media behavior, and a defined-but-not-faked future `/app/interview-studio` owner boundary.
- Exit gate: public/private truth labels, progressive states, desktop/mobile/accessibility evidence, focused and site-rule tests green, completion report reviewed.

## Sequenced after the parallel wave

1. **PS-PLACEMENT-001:** ChatGPT Codex, only after PS-MOMENT-001 proves the canonical Moment boundary; placement stores references, not copied raw text.
2. **Next owner decision:** choose PS-CAPTURE-MEDIA-001/PS-VOICE-001 or owner Home/viewer-mode work after the active wave. Do not infer authorization before manager review.

## Held

- **PS-JOURNAL-001:** Journal UI remains on hold by explicit owner decision.

## Shared rules

- Fetch `origin`; never work directly on `main`.
- One short-lived `work/YYYY-MM-DD-task-name` branch and one active writer per package.
- Handoff requires the branch name and exact full commit SHA.
- Merge through an Azure pull request with squash; delete the task branch afterward.
- Close with `docs/templates/OWNER_TECHNICAL_COMPLETION_REPORT.md`.
- Do not duplicate raw Capture text into surfaces, introduce a second résumé dataset, rewrite authentication, start Journal UI, or claim private behavior the backend does not enforce.
