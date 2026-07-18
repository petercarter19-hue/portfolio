# PeerSlate — Active Initiatives and Lane Assignments

_Updated 2026-07-18 by PS-BASELINE-001._

## Operating model

**ChatGPT Work is the PeerSlate manager.** It owns package sequencing, governance truth, lane boundaries, handoff review, merge readiness, and release verification. Product implementation stays with one writer per branch.

| Lane | Writer | Active package | Reserved domain | Must not touch |
|---|---|---|---|---|
| Governance and orchestration | ChatGPT Work | PS-BASELINE-001 closeout | startup files, `docs/governance/*`, initiative controls, guardrail tests | product routes, migrations, public theme |
| Backend convergence | ChatGPT Codex | PS-CAPTURE-002 | private Capture service/routes, `dbo.*`, migration, backend tests, minimal private Capture controls | public résumé/Studio templates, theme, global nav, auth rewrite |
| Public experience | Claude Code | PS-RESUME-PUBLIC-REFINE-001 | public résumé template/CSS/JS and focused tests | auth, database, Capture, Interview Studio, global theme/nav |

## Parallel start gate

The two product packages may start in parallel only after the PS-BASELINE-001 Azure squash merge is present on `origin/main`. Each writer must fetch, create its own branch from that exact current tip, and record the full base SHA in its first handoff.

### PS-CAPTURE-002 — prepared for ChatGPT Codex

- Branch when accepted: `work/2026-07-18-capture-002` (or the actual start date).
- Source package: `docs/initiatives/PS-CAPTURE-002/README.md`.
- Outcome: owner-scoped correction, archive/restore, explicit delete, and versioned per-capture export over PS-CAPTURE-001.
- Exit gate: migration up/down evidence, negative authorization tests, no automatic publishing, focused and regression tests green, completion report reviewed.

### PS-RESUME-PUBLIC-REFINE-001 — prepared for Claude Code

- Branch when accepted: `work/2026-07-18-resume-public-refine` (or the actual start date).
- Source package: `docs/initiatives/PS-RESUME-PUBLIC-REFINE-001/README.md`.
- Outcome: less repeated hierarchy and a shorter default résumé scan using accessible progressive disclosure, with the same meaning and source data.
- Exit gate: desktop/mobile/accessibility evidence, focused and site-rule tests green, completion report reviewed.

## Sequenced after the parallel wave

1. **PS-INTERVIEW-PUBLIC-GATE-001:** Claude Code, separate branch, only after the route and authenticated-private boundary is defined.
2. **PS-MOMENT-001:** ChatGPT Codex, only after PS-CAPTURE-002 proves source lifecycle and revision behavior.
3. **PS-PLACEMENT-001:** ChatGPT Codex, only after the canonical Moment boundary exists; placement stores references, not copied raw text.

## Held

- **PS-JOURNAL-001:** Journal UI remains on hold by explicit owner decision.

## Shared rules

- Fetch `origin`; never work directly on `main`.
- One short-lived `work/YYYY-MM-DD-task-name` branch and one active writer per package.
- Handoff requires the branch name and exact full commit SHA.
- Merge through an Azure pull request with squash; delete the task branch afterward.
- Close with `docs/templates/OWNER_TECHNICAL_COMPLETION_REPORT.md`.
- Do not duplicate raw Capture text into surfaces, introduce a second résumé dataset, rewrite authentication, or claim private behavior the backend does not enforce.
