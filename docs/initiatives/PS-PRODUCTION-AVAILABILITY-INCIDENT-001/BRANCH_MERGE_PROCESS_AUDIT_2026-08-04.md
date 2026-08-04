# Branch, worktree, merge, and release process audit - August 4, 2026

## Executive conclusion

Azure DevOps squash merging is working. From August 1 through the audit point,
49 completed PRs all reported successful merges. The recurring blockers are
mostly coordination and state-management problems around Git and delivery:

- too many retained worktrees and branches;
- stale or conflicting ownership records;
- stacked branches built on pre-squash parents;
- large PRs that reserve many shared files for a long time;
- infrastructure prerequisites discovered only by the PR build;
- automatic-run visibility lag mistaken for a failed trigger;
- production-capable merges occurring back-to-back without live-verification
  space; and
- status language that collapses branch, PR, merge, deployment, and live truth.

There are also real technical blockers. During this incident the governed
schema pipeline reached its protected environment and failed because a global
CLI argument was placed after a subcommand. That was not a Git merge failure.
PR 276 corrected it after the failure was identified.

## Point-in-time workspace snapshot

| Measure | Observed state |
|---|---:|
| Registered worktrees | 67 |
| Dirty worktrees | 16: 5 tracked-dirty, 11 untracked-only |
| Local branches | 86 |
| Local branches with deleted upstreams | 52 |
| Remote non-main branches | 31 |
| Remote branches with no PR history | 27 |
| Worktrees at least 25 commits behind main | 44 |
| Worktrees at least 75 commits behind main | 31 |
| Detached worktrees | 4 |
| Primary checkout divergence | 101 behind / 4 ahead, with 10 untracked entries |
| Completed PRs since August 1 at snapshot | 49; all merged successfully |
| Azure reviewers on those completed PRs | 0 |

These counts do not authorize cleanup. Dirty, untracked, evidence, and
active-writer worktrees belong to their owners until explicitly classified.
This incident created and then removed one clean detached review worktree; it
did not perform a general cleanup.

## What was actually blocking work

### Worktree and branch accumulation

Git permits a local branch to be checked out in only one worktree. A retained
worktree can therefore make a branch look unavailable even when no current work
is happening. Fifty-two local branches pointed to deleted upstreams, while the
historical open-branch register was not a reliable current ownership ledger.

Five tracked-dirty worktrees require explicit owner review before cleanup. The
Community worktree was one of them and had conflicting writer records:
`CURRENT_BASELINE.yaml` named the current Codex task as sole writer while
Community continuation records named Claude Code as sole active writer. One
authoritative writer must be recorded before runtime edits. This is also why a
blanket prune or delete would be unsafe.

### Infrastructure readiness appeared as merge failure

PR 273 initially failed because protected environment
`peerslate-database-schema` did not yet exist or was not authorized. After the
environment, approval, secret, and pipeline permission were correctly
provisioned, the PR passed and merged. The earlier error was an infrastructure
precondition failure, not a broken merge engine.

The first production schema use then exposed a separate command-wiring bug:

- run 497 passed registry/gate validation and Pete's approval;
- `argparse` rejected `--print-state` after the `apply` subcommand;
- the script failed before any DB connection or SQL execution;
- PR 276 moved the option before all connected subcommands and added regression
  coverage; and
- blocking build 500 passed and PR 276 squash-merged as `304a5ec...`.

The corrected apply in run 501 exposed the next unproven prerequisite. The
environment checks passed, but the hosted job had no usable environment,
workload, managed, CLI, PowerShell, developer-CLI, or broker credential. Azure
SQL never accepted a connection and no migration SQL ran. Environment creation,
approval, and pipeline authorization were therefore necessary but not
sufficient; the pipeline service/workload identity also needs a least-privileged
database principal and a proven token path from the exact hosted task surface.
The separate schema lane has now created a contained Entra database user mapped
to the service principal's application/client ID, with `db_ddladmin`, ledger
DML, audit append, connection, and definition-visibility grants but no broad
member-data or `db_owner` role. PR 278 merged the change that runs connected
commands inside `AzureCLI@2` bound to that Azure Resource Manager service
connection. The remaining precondition is an end-to-end read-only governed
report from the exact hosted task surface; workload identity federation remains
the preferred secretless service-connection direction.

The post-failure production inventory exposed a deeper migration-versioning
blocker. `PS-OPPSLATE-001` was legitimately ledgered when OS-1/OS-2 were applied,
then the same migration file and ID were materially expanded for OS-3. Production
therefore has 8 Opportunity tables and 13 procedures, none of the 4 additional
OS-3 tables or 4 procedures, while the ID already reads as applied. The current
gate expects 186 objects; 61 are missing. Even with authentication repaired, the
planner would not regard the reused ID as pending. This is why migration IDs and
executable bytes must be immutable after first production application; OS-3
needs a new additive ID from the actual OS-2 baseline.

### Oversized and stacked changes

- PR 268 changed 132 files and added approximately 24,700 lines.
- PR 270 changed 63 files and added approximately 12,300 lines.
- Opportunity Slate OS3 and OS4 were stacked: OS3 was an ancestor of OS4 and
  their changed paths heavily overlapped.
- OS4 also had tracked modifications during the audit, confirming an active
  owner-held lane rather than a cleanup candidate.

Azure's required squash merge rewrites the parent into one new commit. A child
branch built on the pre-squash parent will retain the old parent commits and
produce a confusing diff. OS4 must be rebuilt or rebased onto the final OS3
squash result before review.

### Automatic-run visibility and duplicate fallback

Automatic run 490 was queued at 17:46:40 UTC for the exact merge SHA, but it was
absent from normal run listings during the initial observation window. Manual
forced run 491 was then queued for the same SHA while run 490 was already
active. Once the automatic run became visible, the manual duplicate was
canceled before deployment and run 490 was allowed to finish.

The safe inference is not “CI did not trigger.” It is “the normal listing was
temporarily incomplete.” A recovery operator must query by source SHA and, when
necessary, the build API before creating a fallback.

The defect repeated at 18:43:45: the normal list returned zero active runs even
though manual schema run 501 had started six seconds earlier. Querying the
missing numeric build ID exposed it. Active-run guards must therefore combine
the normal list with known/expected IDs or source-SHA build queries during a
high-concurrency incident.

### Back-to-back production-capable changes

During the same incident window:

- PR 273 merged and automatic run 490 deployed;
- PR 274 merged and automatic run 496 deployed;
- manual schema run 497 entered the protected schema stage;
- PR 275 merged and automatic run 499 deployed; and
- two guarded attempts to enable App Service Health Check correctly aborted
  because a production/schema run had become active.
- PR 278 merged and automatic run 505 began deploying; and
- manual run 506 was separately queued to replay the ledgered migration ID while
  run 505 was active, then canceled before its schema stage.
- manual run 507 repeated the same replay request after run 505; its environment
  check was approved, but the schema job was canceled before any task or SQL
  started.
- manual run 508 repeated the request even after schema pipeline authorization
  was removed; it was canceled after Build and before a schema deployment job.

The guards worked, but the sequence shows why operations felt “blocked.” An
incident lane could not safely change App Service or SQL while application and
schema lanes kept entering protected production surfaces.

### Validation, merge, deployment, and live truth were conflated

The blocking PR policy correctly requires fresh CI. It does not provide human
review; the audited PRs had no Azure reviewers. A green PR policy means the
proposed merge passed automation. It does not mean the owner accepted product
behavior, the PR merged, the main pipeline deployed, or production was
live-verified.

PR 278 supplied a concrete failure mode: it merged before review thread 363
appeared. The thread therefore did not gate the stale migration-replay handoff.
Blocking unresolved-comment policy 2 now prevents an already-active discussion
from being ignored, but a production/schema PR still needs an explicit reviewer
before merge when a suitable independent Azure reviewer identity is available.

Likewise, a pipeline task named “Publish evidence” can succeed even when it
uploads zero files. Run 497 demonstrated that task success cannot replace
inspection of the actual artifact and earlier stage result.

### Governance pointers and ownership drift

`CURRENT_BASELINE.yaml` and historical active-package records lagged current
deployments and some current worktrees. Agents following the governance rules
were therefore correct to stop on apparent conflicts, even when a stale record
was part of the conflict. The solution is a refreshed single current ledger,
not permission to ignore ownership checks.

## Controls applied during this incident

- Azure production environment `peerslate-pete` now has Exclusive Lock check
  14. Current YAML stage-level `lockBehavior: runLatest` is already effective;
  the environment check adds defense in depth rather than activating an
  otherwise inert YAML setting.
- The schema environment's approval check remains active. Pipeline 1's
  authorization was temporarily removed after repeated replay runs 506/507; no
  pipeline is currently authorized to enter schema environment 3.
- Main branch blocking comment-resolution policy 2 and squash-only policy 3 are
  active alongside blocking CI policy 1.
- Production Exclusive Lock and schema approval live on different environments;
  they do not provide cross-environment mutual exclusion. Run 505/run 506 proved
  that an app release and schema request can overlap at the queue/build level.
- The duplicate forced run was canceled before deployment; the automatic run
  was not interrupted.
- Guarded plan, Health Check, and SQL mutations were scheduled around protected
  operations. Separately, Azure records an explicit App Service restart at
  18:14:59 during run 496's AzureWebApp deployment task. That task ran from
  18:13:59 to 18:15:47 and production smoke continued to 18:16:22. This overlap
  is direct evidence that manual runtime mutations need the same reservation
  guard as pipeline releases.
- PR 276 fixed the exact schema CLI-order defect, passed blocking CI and an
  independent focused review, squash-merged, and deleted its source branch.
- PR 278's AzureCLI identity-task correction passed blocking build 503 and
  squash-merged as `f59dd9a...`. Review thread 363 recorded its stale replay
  instruction after the merge. Manual runs 506, 507, and 508 then requested that
  reused ID; all were canceled without SQL. Pipeline authorization was removed
  after the second attempt, and a stop notice was posted after the third. The
  identity correction and the new additive OS-3 migration must be treated as
  separate, explicit states.
- PR 276 used `[skip ci]` because its pipeline/test/documentation change did not
  need another application recycle. This is a correct bounded action, not yet a
  durable repository-wide docs-only control.

## Recommended operating model

### One live lane ledger

Maintain one machine-readable current ledger with:

- package and manager;
- active writer;
- worktree path and branch;
- base and current SHA;
- ahead/behind counts;
- reserved shared files;
- dependency/stack parent;
- PR and policy status;
- production/schema surface reservation;
- expiry or review date; and
- disposition: active, blocked, evidence-only, abandoned, or released.

Historical and rejected work belongs in history. A branch or worktree existing
in Git is not proof that it is active.

### Mandatory preflight

Before every write, record:

1. fetched authoritative `origin/main` SHA;
2. worktree path, branch, base SHA, and current SHA;
3. dirty and untracked state;
4. package manager and active writer;
5. ahead/behind counts;
6. overlapping files in active PRs/lanes;
7. infrastructure dependencies introduced by the diff; and
8. PR, pipeline, deployment, schema, and live status when release is in scope.

Proceed only when the lane is current, intentionally owned, and collision-free.

### Infrastructure-readiness gate before PR

When a change introduces an Azure environment, secret, service connection,
managed identity permission, approval, DNS record, or external service:

1. name every prerequisite in the package;
2. identify who may create it;
3. preflight its existence and authorization without exposing secrets;
4. fail before PR policy if it is absent; and
5. record whether the prerequisite is provisioned, validated, and revocable.

This would have turned PR 273's vague blocker into a planned setup step.
For schema operations it must also prove authentication from the actual hosted
job and a read-only SQL command before an approval-gated apply is queued.

### Immutable migration identity

For every production migration:

1. allocate a new ID for every later schema delta or product slice;
2. store the applied executable hash with the ledger record;
3. refuse when repository bytes for an applied ID differ from the applied hash;
4. compute the plan against a fresh read-only inventory of the actual target;
5. gate the additive migration from that exact target baseline; and
6. never edit, delete, or relabel a ledger row to make changed bytes look
   pending.

This turns drift into a pre-approval failure instead of a production surprise.

### Serialize production-capable merges through live verification

1. Merge PR A.
2. Let its automatic main pipeline finish.
3. Verify exact SHA, build, release identity, routes, alerts, and cleanup.
4. Refresh PR B against new main.
5. Repeat.

Do not queue a same-SHA fallback while step 2 or 3 is active. Treat a schema
operation as another production reservation in the same sequence. Add one
shared Azure DevOps environment, orchestration lock, or equivalent pre-stage
mutex so this sequence is mechanically enforced across both app and schema
paths rather than relying on separate environment controls.

### Separate statuses in every handoff

Use explicit states instead of “done” or “failed”:

- branch experiment;
- PR policy validation;
- independently reviewed;
- owner accepted;
- squash-merged;
- main build;
- production deployment;
- live verification;
- schema applied/verified; and
- cleanup complete.

`succeededWithIssues` can truthfully mean build passed and deployment was
intentionally skipped. It does not necessarily mean production failed.

### Bound PR and stack size

- Prefer one independently reviewable behavior change per PR.
- Require an explicit dependency record for stacked branches.
- After a parent squash merge, rebuild the child on current main.
- Require independent review for shared infrastructure, migrations,
  authentication, broad Community changes, or unusually large diffs.
- Avoid reserving shared files across multiple long-lived packages.

### Owner-reviewed cleanup

Do not bulk-delete. Classify each stale worktree/branch as retain, archive/tag,
or delete only after checking tracked changes, untracked evidence, PR history,
and owner relinquishment. Start with clean, gone-upstream lanes. Preserve all
tracked-dirty lanes until their owners decide.

## Prioritized remaining actions

1. Create the live lane ledger and require the preflight output in every agent
   handoff.
2. Add a shared app/schema mutual-exclusion gate and an exact-SHA confirmation
   for forced same-source production redeploys.
3. Before schema approval, mechanically reject any `apply` whose requested ID
   is already ledgered; require a hosted read-only report and a new additive ID.
   Environment authorization prevents execution but does not prevent a wasteful
   queue/build, as run 508 demonstrated.
4. Require explicit production/schema PR review and resolved comments when a
   suitable independent Azure reviewer identity is available. Comment policy 2
   now enforces the latter for threads that exist before merge.
5. Make docs-only production suppression durable instead of relying only on
   author-applied `[skip ci]`.
6. Serialize production-capable merges until slots and multi-instance-safe
   distributed counters exist.
7. Rebuild stacked child branches after parent squash merges.
8. Run an owner-reviewed cleanup sweep; never use a blind branch/worktree purge.
9. Refresh baseline/deployed pointers through bounded governance closeout after
   current release lanes settle.
10. Codify Azure environment checks, monitoring, capacity, and Health Check so
   drift is visible.

## Limits

- Counts are a point-in-time snapshot of this machine and Azure project.
- Claude's complete blocker transcript was not available. The audit explains
  observed blockers but does not claim every message had the same cause.
- No user-owned worktree, local branch, or recoverable artifact was cleaned up.
- The audit does not authorize changes inside active Community or Opportunity
  Slate runtime lanes.
