# PS-INTERVIEW-STUDIO-INTEGRATION-001

## Outcome

Complete the already implemented and independently reviewed Interview Studio
calibration through refreshed exact-SHA verification, Azure PR 325 squash
merge, authoritative-main verification, and bounded cleanup.

This package changes governance records only. It creates no product behavior,
visual direction, route, backend, schema, dependency, pipeline, release, or
production change.

## Authority

Pete directed the team on 2026-08-07 to finish Interview Studio and authorized
the minimum safe governance transition, governed PR merge, debugging, exact
verification, and cleanup after each other. Failed applicable preflights,
Azure policy, ownership, privacy, and evidence gates still fail closed.

The controlling product package remains
`PS-INTERVIEW-STUDIO-CALIBRATION-001`. Its locked visual authority and
five-surface boundary remain unchanged.

## Starting evidence

- Activation base: `58e6a9c1f76a8ab1596a9a16c9b2b4be297900c4`
- Activation PR: 331
- Activation merge: `44562e725fbf67350866ef4507cc81f8753f32aa`
- Existing Interview source before refresh:
  `e695dde2dcd48882106952054fe0a72240bef088`
- Existing Interview PR: 325
- Historical successful build: 613 (`20260807.38`)

Build 613 is evidence only. Any target-main change requires a refreshed
candidate, independent exact-SHA review, and a new successful Azure build.

## Writable boundary

- `docs/governance/CURRENT_LANES.json`
- `docs/governance/CURRENT_BASELINE.yaml`
- `docs/initiatives/PS-INTERVIEW-STUDIO-INTEGRATION-001/`

## Required sequence

1. Pass package write preflight from activation merge.
2. Record Interview merge and cleanup authority without release authority.
3. Validate governance files and delivery controls.
4. Merge the governance PR through Azure policy.
5. Rebase the existing Interview branch onto resulting `origin/main`.
6. Prove patch equivalence with `git range-diff`.
7. Rerun focused tests and independent Sol exact-SHA review.
8. Push only with explicit `--force-with-lease`.
9. Require a new successful Azure build and every PR policy.
10. Pass the Interview package merge preflight.
11. Squash-merge PR 325.
12. Verify authoritative-main tree equivalence and focused tests.
13. Pass cleanup preflight and remove only clean task-local artifacts.
14. Stop before deployment.

## Release truth

This package authorizes no deployment or production change. A successful
merge may be described only as merged into authoritative main, not deployed or
live.
