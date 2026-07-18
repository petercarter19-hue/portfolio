# PS-BASELINE-001 — Verified Baseline and Manager Lane Setup

## Purpose

Reconcile repository governance with the already-merged PS-GOV-001 change, verify production and route boundaries, close document-control gaps, and prepare two non-overlapping implementation packages.

## Owner and branch

- Manager/writer: ChatGPT Work
- Branch: `work/2026-07-18-baseline-lane-setup`
- Verified base: `origin/main @ ec6eae83feedff45d8fe87600e1031253cfd6021`
- Product code ownership: none

## In scope

- Verify Azure repository, PR, pipeline, production-route, Capture, and résumé facts.
- Correct `CURRENT_BASELINE.yaml`, `CURRENT_STATE.md`, and `ACTIVE_INITIATIVES.md`.
- Add document control and the manager decision log.
- Prepare implementation-ready packages for PS-CAPTURE-002 and PS-RESUME-PUBLIC-REFINE-001.
- Strengthen governance guardrails so semantic drift is detected earlier.

## Exclusions

- No application behavior, routes, templates, styles, JavaScript, database code, or migration changes.
- No Capture or résumé implementation.
- No Journal UI, Moment, placement, Interview Studio refinement, auth rewrite, deployment reconfiguration, or GitHub mirror push.

## Entry evidence

- Azure PR 59 was completed.
- `origin/main` was `ec6eae83feedff45d8fe87600e1031253cfd6021`.
- Pipeline 79 succeeded for that commit.
- No active Azure PR existed at audit start.

## Exit gate

- Controlled records agree on authority, manager, active packages, holds, and next sequence.
- Active initiative paths resolve and contain explicit ownership, architecture, tests, exclusions, and handoff prompts.
- Governance and site-rule guardrails pass.
- Azure squash merge and post-merge pipeline are green before either product lane starts.

See the [evidence baseline](01_VERIFIED_BASELINE.md), [boundary matrix](02_BOUNDARY_MATRIX.md), [gap register](03_GAP_REGISTER.md), and [completion report](COMPLETION_REPORT.md).
