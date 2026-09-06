# PeerSlate Repository Instructions

> **MANDATORY PRE-WORK GATE**
> Before a write, migration, deployment, or product decision, open
> [START_HERE.md](START_HERE.md), fetch authoritative Azure `origin/main`, read
> [CURRENT_BASELINE.yaml](docs/governance/CURRENT_BASELINE.yaml), and choose a
> Routine, Bounded, or Protected path. Before an implementation write, read
> [CURRENT_LANES.json](docs/governance/CURRENT_LANES.json) and this package's
> claim under `docs/governance/lane_claims/`, then pass:
>
> `python scripts/delivery_preflight.py --package <PACKAGE-ID> --intent write --task-ref <WRITER-REF> --fetch --require-clean`
>
> A control-only activation, authorize, transfer, owner reassignment, pause,
> resume, or close is the
> narrow exception: run `--intent read` before editing, change and commit only
> the exact package claim on its dedicated control branch, then run the matching
> control intent with `--fetch --require-clean` before PR. Do not change an
> implementation surface in that control commit.
>
> Required-check repair has one separately reviewed admission mode:
> `repair-activate` / `repair-merge`, documented in `START_HERE.md`. It requires
> an exact external owner approval and independent precommit review manifest,
> a current control lease token, and normal Azure CI and branch policies.
> It never converts an ordinary failed preflight into permission.
>
> A failed preflight is a stop, not permission to make another branch or
> worktree. New work requires Pete's explicit outcome and the one-claim
> activation flow in `START_HERE.md`.
> The unrevoked standing bounded Workshop decision recorded in
> `docs/governance/DECISIONS.md` may satisfy that outcome-selection gate only
> for a concrete minimum repository follow-up needed to complete its already
> accepted outcome while the parent claim is active or paused. The child claim
> must cite the standing reference and failed gate; expiry and excluded
> production, schema, destructive, identity/privacy-policy, credential,
> spending, external-operation, and material-visual authorities remain exact.

## Authority

Follow [DOCUMENT_CONTROL.md](docs/governance/DOCUMENT_CONTROL.md). The current
Constitution and Roadmap named by `CURRENT_BASELINE.yaml` control durable rules
and sequence. Historical Bibles, roadmaps, ledgers, status reports, and
handoffs are evidence, not additional gates.

## Always-on product and trust invariants

- Build a reusable multi-user product; Pete is fixture content, never shared
  product logic.
- Content is private by default. Derive identity server-side and authorize
  before returning or mutating protected data.
- Keep canonical truth, source evidence, AI proposals, and projections
  separate. AI proposes; people decide; it never silently saves, publishes,
  sends, deletes, or makes truth canonical.
- Preserve one authoritative source per fact, truthful demo/fixture labels,
  useful AI-unavailable behavior, and WCAG 2.2 AA expectations.
- Preserve unrelated work, secrets, production data, and user-authored content.

## Ownership and delivery

- Equivalent authorized assignments use equivalent lifecycle, delivery and
  review capabilities in Codex, Cursor, Claude and other runtimes. ChatGPT may
  coordinate the program; that role confers no exclusive technical privilege.
  Use each caller's actual opaque reference, never another task's identity.
- Host launchers supply `PEERSLATE_CALLER_REF` for every runtime under the same
  contract. The value is an identity attestation, not a cryptographic boundary
  against another process with the same OS privileges. Use receiver acceptance
  and reviewed owner-revocation recovery when original task continuity is lost;
  do not depend on a permanently reachable chat or infer revocation from age.
- After a control custody transition, use the current lease token for preflight
  and `control-run` for direct control-tree writes. Existing unguarded writers
  require separately established quiescence before recovery; shared tooling
  alone cannot stop raw filesystem writes. Preserve history and existing
  independent precommit and exact-commit merge review.

- One writer owns each mutable surface. Any number of writers may proceed when
  their branches, claimed paths, and hierarchical domains are disjoint. There
  is no numeric writer, class, or production-capable-lane cap. A real branch,
  path, or domain collision stops only the colliding work.
- Review-only agents and independent reviewers do not consume writer claims and
  may not write the implementation branch.
- An assigned implementation writer may implement, validate, correct review
  findings, open the Azure PR, and merge accepted work unless the claim or Pete
  explicitly gives a narrower assignment. No separate merge grant is needed.
- Work on a short-lived branch from current `origin/main`; never push directly
  to `main`. A merge is not a deployment.
- Every merge requires the exact review recorded in its claim: writer
  self-review for Routine/Bounded and independent review for Protected. The
  reviewed candidate stays immutable; later commits may add only the review
  receipt and fixed runtime-inert `lane_claims/evidence/<PACKAGE-ID>.md` file.
- A claim deliberately narrowed to `write_only` cannot merge until Pete's new
  opaque decision reference is recorded by the generic `authorize` control
  transition. Normal implementation claims need no separate merge grant.
- Paused work releases product scope but keeps its branch reserved. Resume uses
  the exact fetched checkpoint and reruns collisions. Preserve the remote
  implementation branch through claim close so reviewed squash bytes remain
  provable.
- A closed package's fixed evidence file may be amended only through the
  owner-authorized `evidence-errata` control transition in `START_HERE.md`;
  the closed claim itself is never reopened or changed.
- Production deployment, schema mutation, configuration, enablement, rollback,
  and destructive operations are separate. A repository claim never grants
  them. Production deployment requires a manually queued exact main SHA and an
  explicit Pete authorization reference; production operations stay serialized.
- Follow [AI model and role routing](docs/AI_MODEL_AND_ROLE_ROUTING.md). Overall
  audit manager, package manager, visual creator, architect, writer, reviewer,
  and release owner are separate assignments; no role silently inherits another.
  Its capability-use section governs useful delegation, browser evidence,
  continuity, goals and scheduling for Codex and Cursor agents. Keep that policy
  canonical rather than copying it into host-specific rules.

## Local worktree lifecycle

- After the `PS-WORKTREE-LIFECYCLE-001` bootstrap, do not run ad hoc
  `git worktree add`. Reuse the active package's one registered durable full
  worktree through `scripts/worktree_lifecycle.py ensure`, or use exact
  bookkeeping-only `adopt` when its claim branch already has a worktree.
- Reviewers default to the immutable Azure/pushed diff and create no worktree.
  They may share the package worktree read-only only when coordinated with its
  writer and there is no concurrent mutation. Runnable isolation leases the
  one sparse `_control` singleton through `verify --runtime-required`.
- Activation, authorize, transfer, owner reassignment, pause, resume, and close
  reuse the same
  mutex- and task-leased `_control` singleton. Successful temporary work is
  finalized in the same task; a refusal preserves the exact path and reports
  the blocker.
- Owner reassignment is a fail-closed recovery, not a voluntary transfer. It
  requires Pete's exact opaque authorization reference, preserves the old
  branch and old-writer worktrees, creates a distinct absent successor branch
  at the exact fetched checkpoint, and records `owner_reassignment` provenance
  without `relinquished`. Preparation requires a complete initialized registry
  with exactly one exclusively leased `_control` record, no lock or unresolved
  pending operation, and no malformed/orphaned preparation state. Every
  pending create, retire, closed-custody-retire, control-repoint, or
  branch-create journal must have
  its exact schema and registry-record custody before reconciliation; recovery
  otherwise leaves the registry unchanged. Preparation reconciles
  every active target/source durable record against its exact pristine live
  Git path, task, branch, and checkpoint; and refuses exact or namespace
  ancestor/descendant branch collisions. It persists one exact completed
  preparation tuple, including Git's `[new branch]` response and source
  snapshot. Owner-reassignment preflight re-proves that tuple and source state;
  post-merge `ensure` consumes it once only while creating a pristine receiver
  worktree; residue retains the pending journal and proof. Preflight performs a
  terminal mutex-held registry/lease/pending validation after all claim and
  remote proofs, and repeats the source, namespace, main, claim, old-branch,
  and successor proofs before releasing that mutex.
  A missing, changed, consumed, duplicated, locked, pending, CI-only, or
  uninitialized proof is a stop. The receiver cannot ensure or write its
  successor worktree until the one-claim recovery PR merges.
  Successive legitimate reassignments retain each older source and preparation
  under its own handoff while binding the new transition only to its current
  source.
  A stale active-durable registry HEAD may be reconciled only inside that same
  preparation transaction, only with a separate bounded source-unavailability
  evidence reference, and only when the recorded HEAD is an ancestor while the
  exact claim/task/branch/path, pristine live checkout, local branch, and
  fetched server tip all prove the requested checkpoint. If guarded successor
  creation proves no new branch, the registry reconciliation rolls back; any
  successful proof is retained in the preparation's digest-bound immutable
  tuple, and its custody record must link bidirectionally to exactly one
  pending or completed/consuming/consumed preparation state. Any omitted or
  orphan link, residue, divergence, lease, ambiguity, or race preserves a refusal. A
  governed `superseded` claim is terminal and is never live ownership.
- Closed-claim worktree retirement by a successor is a separate Protected
  operation, not owner impersonation and not ordinary `retire`. Use
  `retire-closed-custody` only from the exact active cleanup package worktree
  and writer, with Pete's cleanup authorization reference and a distinct
  truthful source-unavailability reference for the one target. Fetched main
  must contain the accepted independent receipt and evidence, every reviewed
  lifecycle surface must have the reviewed bytes on main and the cleanup
  branch, and the executing script blob must be that exact main blob. The fetched
  target claim must be exactly `closed` for the original task and branch; the
  canonical managed path, live checkout, local branch, and server branch must
  all equal the explicit expected HEAD. A stale registry HEAD is admitted only
  when it is equal to or a proven ancestor of that HEAD. The target must have no
  lease, pending operation, duplicate, nesting, reparse point, path ambiguity,
  tracked/untracked/ignored residue, behind-server state, or divergence. The
  transaction preserves the original `task_ref`, records the cleanup caller
  separately with both evidence references, journals exact before/after
  records. Present-side recovery re-proves the complete path, repository,
  branch, live/local HEAD, reparse, nesting, and pristine identity before it
  may clear a preserved journal; every mismatch retains that journal. Removal
  uses only ordinary non-force Git worktree removal. Every branch,
  tag, and ref remains. Any mismatch preserves the target; never reset, clean,
  force, prune, run garbage collection, or delete a ref to make it pass.
- On an initialized machine, mutating preflight requires `--task-ref` and the
  exact registered package or control context. Except for owner reassignment's
  mandatory local preparation proof, CI and an uninitialized machine do not
  create a global block; unrelated grandfathered worktrees never do. Run the
  read-only `worktree_lifecycle.py audit --json` to expose post-policy growth.
- The controlling safety and recovery contract is
  [WORKTREE_LIFECYCLE.md](docs/governance/WORKTREE_LIFECYCLE.md). Never work
  around its refusal with a second checkout, force removal, reset, clean,
  prune, garbage collection, or branch/tag/ref deletion.

## Triggered authorities

| Work area | Read when it applies |
|---|---|
| Shared behavior | [PEERSLATE_SITE_RULES.md](docs/PEERSLATE_SITE_RULES.md) and the package. |
| Material user-facing direction | [OWNER_VISUAL_INTEGRITY_STANDARD.md](docs/governance/OWNER_VISUAL_INTEGRITY_STANDARD.md) and the locked authority. ChatGPT is the sole creator of materially revised production visual direction; writers implement it. |
| Story | [OWNER_STORY_COMPOSITION_STANDARD.md](docs/governance/OWNER_STORY_COMPOSITION_STANDARD.md). |
| Capture/Journal | [PS-JOURNAL-001](docs/initiatives/PS-JOURNAL-001/README.md). |
| Projects | [PS-PROJECTS-001](docs/initiatives/PS-PROJECTS-001/README.md). |
| Protected operations | [PS-OPS-001](docs/initiatives/PS-OPS-001/README.md). |

Use [AI_WORKFLOW.md](docs/AI_WORKFLOW.md). For material closeout, report base
and final SHA, changed paths, verification, review, merge state, deployment
state, honest limitations, and next action. Never call a fixture live, a merge
deployed, or an AI proposal accepted without evidence.
