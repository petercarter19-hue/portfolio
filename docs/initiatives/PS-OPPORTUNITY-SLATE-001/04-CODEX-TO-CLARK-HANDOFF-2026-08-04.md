# PS-OPPORTUNITY-SLATE-001 - Codex to Clark handoff

Date: 2026-08-04

Receiving agent: Clark

Owner goal: Finish the entire public Opportunity Slate page and get it live as
soon as the governed release path can safely support it.

## Read this first

The immediate schema blocker is corrected and proven, but it is **not merged,
applied to production, or live**. Do not claim OS-3 or the whole page is live
until the exact merge, protected schema apply, application deployment, and live
route checks have all been captured.

Use the existing clean additive-schema worktree only after confirming no other
writer has resumed it:

- Worktree: `C:\Users\peter\Documents\portfolio\.wt\oppslate-os3-additive`
- Branch: `work/2026-08-04-oppslate-os3-additive`
- Authoritative base: `af1c6a2216bdb5cddd932fbc3d5c1d0e23ef95b3`
- Proven implementation commit:
  `8797c7fe7394f3f32893a73ab5166c2c0e3b037f`
- Remote proof before this handoff commit: `origin` advertised the same
  implementation SHA for the branch.
- The branch was one commit ahead and zero behind `origin/main` after a fresh
  fetch. The handoff document is a second documentation-only commit on top;
  use the pushed branch tip as the review head.

Codex relinquishes this additive-schema branch after pushing the handoff tip.
Pete remains the release approver. Clark becomes the active writer only after
reconfirming `ACTIVE_INITIATIVES.md` and the package ownership record.

## Total remaining time

From this handoff, the best realistic estimate for **everything remaining on
this page** is **8-14 hours of uninterrupted engineering/release work**. Use
**12-20 hours as the safer planning range** if Azure queues, approvals,
pipeline failures, merge conflicts, or visual acceptance require another
round.

Working breakdown:

- OS-3 schema PR, protected apply, application restack, merge, deploy, and live
  verification: 1.5-3 hours.
- OS-4 saved-details completion, restack, tests, owner visual acceptance,
  release, and live verification: 2-4 hours.
- OS-5b shared dictation cleanup and verification: 1-2 hours.
- OS-6 PDF/DOCX/TXT upload plus public-link import, including parser and SSRF
  hardening: 3-5 hours.
- Final package closeout and end-to-end live evidence: 0.5-1 hour.

These ranges overlap slightly when CI is running. They are not a promise that
Azure approval or owner visual review will be instantaneous.

## Why this took days

This was not one normal page edit. OS-3 and OS-4 were stacked while the OS-3
schema release was still unresolved, and the first OS-3 schema branch changed
the already-ledgered migration ID `PS-OPPSLATE-001`. Production already held
that ID for the OS-1/OS-2 shape. The governed path correctly refused to treat
different bytes under the same immutable ID as a new release.

Several pipeline attempts then failed or were canceled for different reasons:

- Run 497 failed before SQL because the schema CLI options were ordered
  incorrectly.
- Run 501 reached credential acquisition but failed closed because the hosted
  shell had no usable Entra credential.
- Runs 506, 507, and 508 were canceled; none supplied evidence of SQL apply.
- Run 511 reached production and refused the reused `PS-OPPSLATE-001` ID as a
  no-op/drift condition. It did not apply OS-3 SQL.

The repository audit at current main makes the required correction explicit:
restore 001 to its original immutable bytes and ship OS-3 under a new additive
ID. That is what this branch does.

## What is complete on the handoff branch

1. `PS-OPPSLATE-001` is restored byte-for-byte to the OS-1/OS-2 form from
   commit `95d184e2846023bbf0134af43911ae6a3d1b4a15`.
2. New `PS-OPPSLATE-002` adds the four OS-3 tables and the OS-3 procedure delta
   without rewriting the 001 ledger row.
3. The 002 rollback refuses member rows, later migrations, or owned-procedure
   drift; restores the four modified 001 procedures; drops the four new
   procedures and tables; and deletes only the 002 ledger row.
4. Registry and tests now model 001 as the immutable baseline and 002 as the
   additive OS-3 delta.
5. The completion report and governed-gate evidence have been corrected so
   they no longer present the reused 001 attempt as releasable truth.

Exact governed hashes:

- `PS-OPPSLATE-001`:
  `2406ff6eedd44939ee5148982462a66935f13dfea45fe46076cf5895883c7273`
- `PS-OPPSLATE-002`:
  `2af25b7d4f04984d88a30b7d65bc1948bc4bba810ab048963b4cd85a8d471dd0`

## Verification completed

Disposable Azure SQL database:
`ps-oppslate-additive-gate-20260804` on server `peerslate`.

- 001 gate passed prerequisites, forward apply of 125 objects, no-op reapply,
  `verified = 1`, rollback of 125 objects, and forward reapply.
- 002 gate passed prerequisites including 001, forward apply of 61 objects,
  no-op reapply, `verified = 1`, rollback of 61 objects, and forward reapply.
- The disposable database was deleted. A subsequent Azure resource lookup
  returned `ResourceNotFound`.
- `python -m unittest tests.test_opportunity_slate_migration
  tests.test_schema_migration_path`: **116 passed, 3 skipped**.
- Wider affected Opportunity Slate/database/operational suite: **309 passed, 3
  skipped**.
- Registry: **24 registered, 12 gated and matching; internally consistent**.
- `git diff --check`: pass.

Primary evidence:

- `OS-3_SCHEMA_RELEASE_COMPLETION_REPORT.md`
- `evidence/os-3/sql-gate-governed.json`
- `SQL FIles/Migrations/registry.json`

## Current production and pipeline truth

After a fresh fetch, authoritative `origin/main` is still
`af1c6a2216bdb5cddd932fbc3d5c1d0e23ef95b3`.

The latest pipeline query at handoff showed:

- Run 511: completed/failed on exact main SHA `af1c6a2...`.
- Run 505: completed/succeeded on application SHA `f59dd9a...`.
- Runs 506-508: canceled on `f59dd9a...`.

Therefore the last verified deployed application identity remains
`f59dd9adb8d3da3e6faaae6691ecad1f801b0c2d` / run 505, while current main adds
the later documentation-only incident audit. Production has the OS-1/OS-2
`PS-OPPSLATE-001` ledger state. It does **not** have `PS-OPPSLATE-002`.

The protected environment permission for pipeline 1 is already granted for
`peerslate-database-schema`. The Azure service connection uses application
client ID `8948ceff-6f5c-4f88-91cd-aefc6e99fc32`, mapped to the contained
database principal `peerslate-ado-schema`. Do not broaden that principal or add
a SQL password/firewall exception.

## Exact next sequence

1. Read `START_HERE.md`, the current baseline/state/initiatives, current Bible
   and Roadmap, `PS-OPPORTUNITY-SLATE-001`, and the August 4 incident audit.
2. In the additive worktree, run `git fetch origin --prune`; verify main has not
   moved and review the complete `origin/main...HEAD` diff.
3. Re-run the registry check and the two test commands above if any byte
   changes. Do not edit 001 unless restoring its verified immutable bytes.
4. Open an Azure DevOps PR from
   `work/2026-08-04-oppslate-os3-additive` to `main`; wait for all blocking
   validation; use the required squash merge; record the exact merge SHA.
5. Wait for the automatic main run on that exact merge SHA to finish. Do not
   queue a duplicate same-SHA fallback while it is active.
6. Queue the existing manual schema pipeline with:
   `schemaAction=apply`, `schemaMigrationId=PS-OPPSLATE-002`, and
   `forceProductionDeploy=false`.
7. At the protected-environment approval, approve only if the plan shows
   `PS-OPPSLATE-002` and executable hash
   `2af25b7d4f04984d88a30b7d65bc1948bc4bba810ab048963b4cd85a8d471dd0`.
8. Verify the exact run, successful SchemaMigration stage, production 002
   ledger row/hash, expected tables/procedures, and emitted migration evidence.
9. Only then restack the OS-3 application branch onto current main. Resolve its
   old schema references in favor of the merged 001+002 contract; do not bring
   back the reused-001 migration. Re-run focused and repository checks, open
   the application PR, merge, deploy, and live-verify the public route.
10. Continue OS-4, OS-5b, and OS-6 in order, preserving their separate gates
    and truth labels. Finish with package closeout and exact live evidence.

## Existing stacked branches and worktrees

### OS-3 application

- Worktree: `C:\Users\peter\Documents\portfolio\.wt\oppslate-os3`
- Branch: `work/2026-08-04-opportunity-slate-os3`
- Current SHA: `3ac0e9d5a5fb0a20ce1c9f70b1d73ae1ea2f02a9`
- Remote is pushed.
- Worktree contains user/agent-owned untracked `artifacts/2026-08-04-os3/`
  and `output/`. Preserve them.
- Earlier verification: focused **351 passed, 2 skipped**; broad **2,391
  passed, 9 skipped, 1 deselected; 3,200 subtests**.
- Do not merge it as-is. It predates the additive correction and must be
  restacked after production 002 is verified.

### OS-4 saved details

- Worktree: `C:\Users\peter\Documents\portfolio\.wt\oppslate-os4`
- Branch: `work/2026-08-04-opportunity-slate-os4`
- Current committed SHA: `de8735ced7673685ef7909b9d4bd72490b74f0c3`
- The worktree has legitimate uncommitted corrections across migration,
  report/evidence, route/service/template, and tests. Preserve every one of
  them; do not reset, clean, or overwrite the worktree.
- Restack only after OS-3 app lands. Saved-details visual acceptance is still
  required before release.

### Superseded experiment - do not use

- Worktree: `C:\Users\peter\Documents\portfolio\.wt\oppslate-os3-schema`
- Branch: `work/2026-08-04-schema-revision-aware`
- This contains the abandoned revision-aware attempt and uncommitted work. It
  is superseded by `PS-OPPSLATE-002`. Do not merge, clean, or delete it during
  this release.

## Owner decisions already made

- Proceed with OS-3. The semantic false-positive limitation is accepted for
  the current small, unpromoted demo audience.
- Keep a 24px shared-card gap.
- Defer the filter to OS-4.
- Keep the closing strip.
- Fixture/demo information is acceptable when labeled truthfully; do not
  represent it as production-backed member truth.
- The owner wants the full page live as quickly as possible, but merge,
  deployment, and live claims still require their corresponding evidence.

## Remaining feature scope after OS-3

- **OS-4:** Saved-details behavior and visual acceptance.
- **OS-5b:** Replace literal 10-second dictation text with the shared derived
  `silenceMs` value and complete shared dictation verification.
- **OS-6:** PDF, DOCX, and TXT upload plus public-link import, with file limits,
  parser safety, URL validation, redirect/private-network SSRF defenses,
  truthful error states, and no silent canonical save.
- **Closeout:** End-to-end public-route checks, responsive/keyboard evidence,
  exact deployment identity, package status, and final owner technical
  completion report.

Clark should lead with the release truth on every update: what is discussed,
implemented, pushed, merged, schema-applied, deployed, and live are separate
states.
