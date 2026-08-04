# PS-DELIVERY-RESET-001 - Delivery control-plane reset

## Authority and outcome

- Owner authorization: Pete's August 4, 2026 direction to stop current work and
  start the reset so every lane returns to one reliable operating system.
- Delivery path: Protected operational coordination. This package changes the
  shared delivery control plane, but it changes no product behavior, member
  data, schema, production setting, or live route.
- Designated manager and sole writer: the current Codex reset task.
- Branch: `work/2026-08-04-delivery-reset-001`.
- Authoritative base:
  `af1c6a2216bdb5cddd932fbc3d5c1d0e23ef95b3` from Azure DevOps
  `origin/main`.
- Writable surface: this package, `CURRENT_BASELINE.yaml`,
  `CURRENT_LANES.json`, the root startup routers, the delivery preflight, and
  their focused tests; plus the bounded PS-OPS production-operation pipeline,
  schema preflight, documentation, and regression tests needed for R2.

The immediate outcome is one owner-directed temporary freeze with one write
lane. Existing work is preserved at its current branch/SHA and becomes
read-only until it is explicitly retained, reassigned, archived, or released.

## Safe-stop rule

Every other lane must stop before its next write, merge, deployment, schema
operation, or new worktree. A writer may finish only the atomic preservation
step already in progress, then reports:

- package and owner;
- worktree and branch;
- exact pushed SHA, or exact dirty/untracked state when pushing would be unsafe;
- active PR/pipeline, if any;
- files or shared surfaces reserved; and
- explicit ownership relinquishment.

Stopping never means resetting, cleaning, deleting, stashing, force-pushing,
or abandoning another writer's material.

## Verified reset-entry snapshot

Captured at `2026-08-04T21:45:30Z` after fetching Azure authority:

- `origin/main`: `af1c6a2216bdb5cddd932fbc3d5c1d0e23ef95b3`;
- active Azure pull requests: 0;
- queued or running Azure pipelines: 0;
- live application source: `f59dd9adb8d3da3e6faaae6691ecad1f801b0c2d`,
  successful automatic pipeline 505, live release
  `21a77fc14df89aa4f4397f2d`;
- registered worktrees: 69;
- local branches: 93, including 57 whose upstream is gone;
- remote non-main branches: 32;
- dirty worktrees: 17 after exact reinspection: 6 with tracked edits and 11
  with untracked material only;
- worktrees at least 25 commits behind main: 46; and
- worktrees at least 75 commits behind main: 33.

These counts authorize inventory and classification, not deletion by count
alone. Pete subsequently authorized controlled cleanup on August 4, 2026.
Only the reset lane may remove an exact target after it is verified clean,
classified, and protected by a recovery ref. Ambiguous or untracked material
remains preserved.

## Reset phases

### R0 - Freeze and truth alignment

1. Make this package the only writable lane.
2. Publish `CURRENT_LANES.json` as the compact machine-readable lane ledger.
3. Correct current release, theme, ownership, and next-gate pointers.
4. Require the executable preflight from every current startup router.
5. Publish the plain-English owner delivery guide.
6. Preserve all existing branches, worktrees, and artifacts.

### R1 - Owner-reviewed workspace disposition

1. Obtain each active writer's exact safe-stop report where a writer is still
   reachable; otherwise preserve and classify the recorded checkpoint.
2. Classify each worktree and branch as retain, archive, delete-candidate, or
   evidence-only.
3. Start with clean worktrees whose upstream is gone and whose PR is merged.
4. Preserve every untracked or otherwise ambiguous worktree until its contents
   and owner are known.
5. Create a recovery ref for every branch tip before removing its clean
   worktree or local branch.
6. Delete nothing in bulk or solely because its upstream is gone.

The cleanup log records 24 exact clean worktrees and 43 local branches removed
after Azure/ancestry proof and recovery refs. The remaining-workspace inventory
records every preserved worktree and branch with its exact checkpoint. All
pre-existing dirty/untracked worktrees were preserved.

### R2 - Mechanical release and schema controls

1. Use one shared production reservation across application and schema paths.
2. Reject an `apply` request before approval when its migration ID is already
   ledgered or its applied digest does not match repository bytes.
3. Require a hosted read-only database report before the next schema apply.
4. Require a source-SHA query before any manual production fallback.
5. Make documentation-only pipeline suppression deterministic.

Implemented in this package:

- `ProductionOperation` is one stage-level sequential reservation shared by
  application deployment and schema work. One run cannot request both.
- A forced manual application fallback must name the exact 40-character main
  SHA. Azure is queried before the operation, and the fallback is refused when
  an automatic exact-SHA run is active or has already succeeded.
- Schema apply and rollback require one named migration; apply no longer means
  "apply every pending migration."
- A hosted read-only ledger and gate-digest preflight runs inside the shared
  reservation before the schema approval is requested. An already-ledgered
  ID, changed gated bytes, unexpected plan, or invalid rollback target fails
  before approval and before mutation.
- The migration registry check also runs explicitly in Build, before any
  production-operation stage can begin.

Documentation-only deploy suppression remains the existing final-squash
`[skip ci]` contract. It cannot be inferred solely from paths because selected
governance and knowledge documents are runtime inputs. The reset makes the
owner/manager responsible for the final squash message and tests that the rule
remains explicit; automatic path-only suppression would be incorrect.

### R3 - Controlled restart

Pete explicitly ends the freeze only after the exit criteria pass. Restart
with no more than:

- one production-capable lane;
- two non-overlapping implementation lanes total;
- one product/visual discovery lane that creates no runtime branch before an
  exact activation; and
- one merge followed by its automatic pipeline and live verification before
  the next production-capable merge.

## Current protected stops

- Community public pilot remains flag-off. Re-enablement requires one writer,
  request-path maintenance removal, bounded dependency waits, and the package's
  release evidence.
- Opportunity Slate OS-3 remains unapplied. `PS-OPPSLATE-001` is already
  ledgered at the OS-1/OS-2 shape; OS-3 requires a new immutable additive ID
  from the actual production baseline.
- Opportunity Slate OS-4 remains parked until OS-3 is rebuilt from its final
  squash result and separately accepted.
- No non-reset PR merge, manual pipeline, deployment, schema operation,
  production-setting change, or new implementation worktree is authorized
  during R0. The reset's documentation-only PR is the sole merge exception.

## Reset exit criteria

The temporary freeze may end only when all of the following are true:

- the baseline and live-lane ledger agree with fetched Azure and live release
  evidence;
- all prior lanes have an owner, disposition, and exact branch/SHA or preserved
  dirty-state record;
- the primary session-start path uses current startup instructions;
- clean stale worktree/branch cleanup has received owner-reviewed disposition;
- application/schema serialization and migration-identity stops are
  mechanically enforceable;
- no queued/running production-capable operation is unexplained; and
- Pete selects the first post-reset production outcome and explicitly releases
  only the needed lane or lanes.

## Explicit exclusions

R0 does not implement Community, Opportunity Slate, Workshop, Journal, Profile,
Owner Home, Capture, theme, or other product work. It does not delete branches,
worktrees, artifacts, stashes, migrations, production data, or Azure resources.
It does not merge, deploy, or apply schema merely to make records look current.
