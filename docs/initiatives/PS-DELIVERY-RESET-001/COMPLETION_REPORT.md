# PS-DELIVERY-RESET-001 completion record

## Core record

- Task/package and delivery path: `PS-DELIVERY-RESET-001`, Protected shared
  delivery-control and production-operation correction.
- Outcome and member/site effect: the primary session entry now uses current
  Azure-main instructions; legacy work is paused and inventoried; verified
  redundant local worktrees/branches were removed behind recovery refs; one
  machine-readable lane ledger and executable preflight now fail closed; and
  web deployment plus schema work share one serialized production-operation
  stage. No member-facing route, product behavior, production configuration,
  database row, or schema object was changed by this package.
- Branch, base SHA, final SHA, and changed paths: branch
  `work/2026-08-04-delivery-reset-001`; base
  `af1c6a2216bdb5cddd932fbc3d5c1d0e23ef95b3`; implementation completion SHA
  `eadebb62d5d3c7ad3e5fe4788995965f0976fe9a`; final report commit and Azure
  reset squash SHA `f706d6cd678c3e3b2b39228d98fee85afd9aea03` from
  Azure PR 279; the final controlled-idle record SHA is supplied by its PR
  handoff because a commit cannot contain its own SHA. Paths:
  root startup routers; `azure-pipelines.yml`; `CURRENT_BASELINE.yaml`;
  `CURRENT_LANES.json`; startup checklist and owner guide; this reset package;
  the PS-OPS schema-operation records; delivery, production-operation, and
  schema scripts; and their focused governance/operational tests.
- Verification performed and result:
  - Pass: current reset/closeout-focused `unittest` run, 110 passed and 1
    skipped across 111 tests.
  - Pass: Python 3.12 `compileall` for the CI runtime/operational surface.
  - Pass: migration registry check, 23 registered and all 11 gate proofs
    matching repository bytes.
  - Pass: `CURRENT_LANES.json` parse, generic YAML parse, and `git diff
    --check`.
  - Pass: executable delivery preflight for reset/write on the exact branch and
    Azure base.
  - Pass: required Azure PR validation build 512, including the full Linux
    suite, dependency and history-secret scans, compile, migration registry,
    and deployment-artifact construction.
  - Baseline note: full local Windows suite ran 2,358 tests with 2 failures and
    29 skips. Both failures predate and are outside this diff: POSIX `0600`
    permission assertion on Windows and Windows MIME lookup returning
    `application/octet-stream` for `.webp`. The authoritative Linux Azure PR
    validation passed the full suite and pipeline-schema check.
- Release state: reset controls squash-merged through Azure PR 279 at
  `f706d6cd678c3e3b2b39228d98fee85afd9aea03`; validation build 512 succeeded;
  no main pipeline, application deployment, production configuration change,
  or schema action was queued. Live remained healthy on prior release
  `21a77fc14df89aa4f4397f2d`. The controlled-idle closeout record is pending its
  final documentation-only PR.
- Known limits, deferred work, or owner decision needed: 45 worktrees, 50 local
  branches, and 32 remote non-main branches remain by design. Seventeen
  worktrees contain tracked or untracked material and 27 clean non-reset
  worktrees lack sufficient deletion proof. Community remains flag-off;
  Opportunity Slate OS-3 remains unapplied. A hosted read-only schema report
  is required before the next apply. Pete must select the first post-reset
  production outcome before any former lane is reactivated.
- Next action: validate and merge the controlled-idle closeout record, remove
  its clean branch/worktree behind the existing recovery ref, and remain idle
  until Pete selects one outcome. That selection uses the bounded ledger-only
  activation policy before any implementation worktree is created.

## Protected additions

- Shared infrastructure contract changed: application deployment and schema
  actions now share the `ProductionOperation` stage lock; one run cannot ask
  for both. A manual web fallback must name the exact 40-character main SHA
  and is refused when an automatic exact-SHA run is active or succeeded.
- Migration control changed: apply and rollback require one migration ID; a
  read-only live-ledger and gate-digest preflight runs before the database
  approval; apply receives both `--migration` and `--expect` for that ID.
- Negative-path evidence: focused tests cover duplicate automatic runs,
  malformed/mismatched manual SHA, mixed web/schema requests, missing or
  mismatched migration IDs, already-ledgered apply, stale gated bytes,
  unexpected plan, and invalid rollback target.
- Rollback/stop: these controls change orchestration only. Revert the reset
  squash through a new Azure PR if pipeline compilation exposes a flaw; do not
  manually run production or schema as a workaround. Existing schema rollback
  remains explicit, latest-only, two-value-confirmed, and approval-gated.
- Monitoring/operational owner: Pete owns production authority; the package
  manager owns PR/policy observation and the exact post-merge primary
  fast-forward. Azure required policy is the remaining review gate. No
  production observation window is created because this package must not
  release runtime or schema.

Overall status: **Conditional** only until the final controlled-idle ledger is
validated and squash-merged. The reset controls, primary fast-forward, safe
cleanup, and no-deploy verification are complete.
