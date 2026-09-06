# Pete's PeerSlate Delivery Guide

## The simple rule

Ideas are unlimited. Writers are also not limited by a fixed number. The real
limit is collision: one writer per mutable surface, one branch per package, and
no overlapping hierarchical domain. Disjoint work proceeds independently.

## What an assignment permits

| Assignment | Default authority |
|---|---|
| Discovery/review | Read, analyze, and report only. No writer claim. |
| Implementation | Implement, test, self-review, correct findings, open the PR, and merge the accepted repository change. |
| Explicitly narrower task | Only the boundary Pete or the claim states. |
| Production operation | Never inherited from repository work; Pete separately authorizes the exact action and SHA. |

A complete owner-authorized package transfer to Cursor, Claude, Grok, or
another supported environment may make its accepted manager responsible for
the bounded package through closeout. It needs no Codex supervisor. Verify the
receiving task, actual platform/account/project/repository access, exact
source, configured and effective model/effort, and explicit acceptance first.
Portable instructions never make credentials or session authority portable.

Independent review remains useful without becoming another waiting writer. The
reviewer reads the frozen SHA and evidence, returns findings, and does not own
the implementation branch. The writer corrects findings and records the final
exact-SHA receipt. Routine and Bounded work use the same receipt path with
`review_type: self` and the writer's opaque task reference, so they do not wait
for an independent reviewer.

If Pete explicitly narrows an implementation claim to `write_only`, that claim
can build and test but cannot merge. Pete can later expand the same assignment
through a tiny `delivery-authorize` control PR that records a new opaque owner
decision reference; no person's account identity is needed.

## Five truthful stages

1. **Select.** Pete names one outcome; discussion alone opens nothing.
2. **Claim.** A tiny JSON claim reserves branch, paths, domains, and delivery
   path. It always withholds production authority.
3. **Build.** The assigned writer works independently unless a real collision
   appears.
4. **Review and merge.** Tests, self-review, triggered independent review, PR,
   CI, and merge are recorded separately. The implementation assignment normally
   continues through merge.
5. **Operate or close.** Deployment or schema is a separate explicit decision.
   If no production operation is authorized, close the repository claim after
   the merged CI-only result is verified.

## Collision examples

- Two packages claim different templates and different domains: both proceed.
- Two packages claim the same file or one claims a parent directory of the
  other's file: the colliding package waits or transfers scope.
- Two packages claim `shared:auth` and `shared:auth:callback`: collision.
- Main advances only in paths outside the reviewed claim: review remains valid.
- Main advances inside the reviewed claim: merge stops for reconciliation.

There is no four-writer, shared-foundation, direction, or production-capable
slot. A reviewer consumes no writer claim. Paused and closed claims do not block
new product work. A paused claim keeps its preserved branch name; every
package's claim, receipt, and evidence paths remain permanently package-owned.

## Permission boundaries

- A claim is repository authority, never production authority.
- A merge is not a deployment.
- PR and automatic main runs build and test only.
- A production web deployment requires a manual main run, the exact full main
  SHA, `forceProductionDeploy=true`, and a bounded reference to Pete's explicit
  authorization.
- Schema actions are manual, separately checked, and cannot share a web
  deployment run.
- Production operations are serialized through Azure environment locks.

## Copy-paste directions

### Explore only

> Discovery only. Give me evidence, risks, options, and a recommendation. Do
> not create a claim, branch, worktree, code change, PR, deployment, or
> production change.

### Assign implementation

> Implement [exact outcome]. Claim only [paths/domains]. You may implement,
> test, self-review, correct review findings, open the Azure PR, and merge once
> the required checks and review pass. Stop before deployment or any production
> mutation unless I explicitly authorize that exact operation later.

### Assign review only

> Review exact candidate [SHA] for [package]. Read only. Return prioritized
> findings and a pass/reject result; do not edit, commit, push, merge, deploy,
> or take a writer claim.

### Expand an explicitly narrowed assignment

> I expand package [PACKAGE] from `write_only` to repository authority through
> merge. Record this decision as opaque reference [task/session reference] on a
> `delivery-authorize` control branch. Do not deploy or mutate production.

### Transfer ownership

> The prior writer pushed [SHA] and relinquishes [package]. Transfer the claim
> from exact task reference [from] to [to], preserving branch and scope. Record
> receiver [platform/task], the stable non-secret account/organization,
> project, and repository identifiers used to verify access, configured and
> effective model/effort, the successful source-access check, and explicit
> receiver acceptance. Do not request or transfer credentials, MFA, tokens,
> cookies, browser state, private session files, or session-only authority.

### Recover ownership without relinquishment

> I authorize owner-reassignment recovery for [PACKAGE] from opaque writer
> reference [from] to [to], with authorization reference [owner reference].
> Preserve old branch [old branch] and all old-writer worktrees. Create only
> absent successor branch [new branch] at exact fetched old checkpoint [SHA],
> after reconciling every active source durable record and all branch-namespace
> custody. Persist and revalidate the exact completed server/source preparation
> tuple on a complete initialized registry with exactly one unlocked,
> receiver-leased control record; reject malformed/orphaned preparation state,
> any pending operation without exact schema and record custody, namespace
> collisions, and terminal mutex-held registry/lease/pending/source/remote
> races after all owner proofs. Do not
> allow CI/uninitialized bypass or replay it after its one post-merge consume,
> and do not consume it if the receiver worktree has any residue.
> Then change only claim `writer_ref`, `branch`, and the truthful
> `owner_reassignment` handoff. Never assert relinquishment, force-move or
> delete a ref, or let the receiver write before the control PR merges. Stop on
> any collision, race, dirty/moved/ambiguous source, pending registry state, or
> ambiguous server proof.
> For a later authorized reassignment, retain every older source and consumed
> tuple under its own handoff and bind only the current source to the new tuple.

### Resume preserved work

> Resume [PACKAGE] from its recorded pushed checkpoint. Change only paused to
> active on a `delivery-resume` control branch, verify the remote tip still
> matches, and stop if current branch/path/domain collisions exist.

### Authorize a deployment

> I explicitly authorize production deployment of exact main SHA [40-char SHA]
> for [package/decision reference]. Queue one manual main run with that SHA and
> authorization reference. Do not combine it with schema, configuration,
> enablement, rollback, or another production operation.

## Reading status

Ask for these separately: selected, claimed, implemented, tests passed,
self-reviewed, independently reviewed when required, PR policy passed, merged,
CI-only main build passed, deployment authorized, deployed, live verified,
schema applied, and claim closed. Preserve the remote implementation branch
through close; a squash close proof needs that exact reviewed candidate. “Done”
is not a substitute for the exact state.

The system succeeds when everyone can do their assigned repository work without
permission theater, while actual collisions and production operations remain
visible and fail closed.
