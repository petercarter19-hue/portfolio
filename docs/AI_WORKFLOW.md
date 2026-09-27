# PeerSlate Lean Delivery Workflow

_One writer per mutable surface; unlimited disjoint work; explicit production
operations._

## Default flow

Equivalent assignments keep the same lifecycle across runtimes. Preserve
caller identity and reviewed acceptance. `docs/governance/WORKTREE_LIFECYCLE.md` governs
custody recovery; `START_HERE.md` governs required-check repair without
waiving Azure CI or branch policies. Configuration does not prove access.

1. Follow `START_HERE.md`, fetch Azure main, preserve unrelated work, and read
   the current package claim.
2. Choose Routine, Bounded, or Protected. Reuse the registered durable
   worktree and pass its exact writer `--task-ref` to mutating preflight;
   `ensure` provides non-gating readiness.
3. The assigned writer implements, validates, self-reviews the complete diff,
   corrects findings, opens the PR, and merges accepted work.
4. Add an independent exact-SHA review only when Protected risk, the package,
   or Pete requires it. The reviewer is read-only, consumes no writer claim,
   and defaults to the Azure/pushed diff without creating a worktree.
5. Report merge, deployment, schema, enablement, and live verification as
   separate states.

For writable packages, commit the focused baseline and criteria in the fixed
evidence file before coding. After review, map each criterion to semantic,
candidate-bound source proof and invoke
`python -B scripts/package_acceptance.py check --package <PACKAGE-ID> --candidate <REVIEWED-SHA>`
before accepting completion. Read-only work uses `--read-only`. This agent-executed check is
neither delivery preflight nor an OS write gate; see `START_HERE.md`.

Specialist reviews and audits are event-driven; none is required
unless its delivery path or package specifically triggers it. Use
[capability routing](AI_MODEL_AND_ROLE_ROUTING.md#capability-use) for model and tool choices.

## Concurrency and collision rule

Writers have no capacity cap when branches, paths, and hierarchical domains
are disjoint. Reviewers claim no mutable surface. Each package keeps its claim,
receipt, and evidence namespace. Paused work releases product scope but
reserves its branch; closed work keeps historical control custody. Collisions
stop only affected packages. Disjoint main movement preserves review; claimed
surface movement expires it.

Scope reduction requires the durable `scope-release` freeze and claim-only
`release-surfaces` transition. Journaled `reconcile-main` then imports
authoritative main without admitting unowned conflicts or granting PASS.

## Worktree lifecycle

Ad hoc `git worktree add` is unsupported. Use `ensure` or exact `adopt`
for the durable worktree; reviews create none. Control transitions and runnable
isolation lease the sparse `_control` singleton and finalize in the same
task. The local registry guards workspace custody, not repository authority;
`audit` is read-only. Retirement follows
`docs/governance/WORKTREE_LIFECYCLE.md` with ordinary non-force Git removal.

## Delivery paths

| Path | Typical work | Required control |
|---|---|---|
| Routine | Copy, isolated visual correction within locked authority, local refactor, focused test, documentation | One writer, focused validation, self-review. |
| Bounded | Approved route or feature within an established package | Package contract, focused tests, ordinary PR. |
| Protected | Identity, authorization, privacy, canonical truth, migration, deletion/publication, consequential AI, shared infrastructure/configuration, major availability risk, or materially revised visual direction | Named risk contract, negative/rollback evidence as applicable, and independent exact-SHA review. |

Protected release and production-operation work also uses `PS-OPS-001`.

## Integrity rules

- Azure `origin/main` is authoritative; never push directly to main.
- One writer owns a mutable surface. Preserve unrelated work and secrets.
- Private is the default. Derive identity server-side and authorize before
  returning or changing protected data.
- AI proposes; people decide. Keep canonical truth, evidence, proposals, and
  projections separate.
- Preserve truthful labels, accessible responsive behavior, and useful
  AI-unavailable paths.
- ChatGPT creates materially revised production visual direction and the owner
  accepts it; implementation agents adapt only within the locked authority.

## Review and repository release

The implementation writer has repository authority through merge unless the
claim is explicitly `write_only`. Reviewers are claim-free.
No separate owner merge grant is required.

Every merge requires one frozen, pushed candidate and receipt.
Routine and Bounded writers complete self-review and issue a `self` receipt
whose opaque reviewer reference equals their writer reference. Protected work
uses the required read-only independent reviewer. Correct findings and freeze
again until one exact candidate passes. The writer may then add only the
generic review receipt and fixed runtime-inert
`lane_claims/evidence/<PACKAGE-ID>.md`. Merge preflight verifies the reviewed
SHA, receipt, remote branch tip, claimed paths, evidence-only tail, and
non-colliding main movement.

A `write_only` claim cannot merge. Pete may expand that assignment through a
`delivery-authorize` control PR changing only
`repository_authority` from `write_only` to `through_merge` and replace
`owner_outcome_ref` with the new opaque decision reference. Validate it with
`--intent authorize`, merge the control PR, and then use the ordinary review
and merge path. This transition is not needed for normal implementation claims.

Use an Azure PR. Current-target CI and unresolved comments still apply. A green
PR or a merge is repository truth, not deployment truth.

Run merge preflight in the clean durable worktree with the exact writer task
reference. Historical candidates preserve their old branch bytes.

### Documentation-only closeout

For bookkeeping that is not runtime-consumed, merge with `[skip ci]` in the
final squash message. Do not restart App Service merely to publish bookkeeping.

## Production boundary

PR/main runs are CI-only. Production needs an exact main SHA, Pete's explicit
reference, environment lock, rollback/disable path, and post-operation journey
proof. Schema actions stay manual and mutually exclusive with web deployment.
A green PR or merge is never live proof.

## Handoffs and closeout

Use `MANAGER_SESSION_HANDOFF.md` only when ownership actually changes. Package,
branch, pushed SHA, opaque task references, relinquishment, scope, evidence, and
next action are sufficient; no real-world identity disclosure is required.

Pause only at an exact pushed checkpoint. Resume through the one-claim
`delivery-resume` transition; it changes only paused to active, proves the
fetched checkpoint, and reruns collisions. Preserve the remote implementation
branch through close so squash-merge byte proof remains reproducible. If it was
deleted, re-push the exact reviewed branch before retrying close.

After resume or partial release, `reconcile-main` pins C/M, permits only retained
owned resolution, makes a normal two-parent merge, and never force-pushes. Main
drift preserves R as `refresh_required`; fresh reconciliation and exact review
cover changed combined bytes.

Record outcome, SHAs, changes, tests, acceptance-check result, review, release
states, limits, next action, and exact-session `finalize-task` usage or
unavailable once. Candidate,
Launch, Operate, Retire, visual acceptance, and full-site audits are
event-driven. None blocks unrelated Routine or Bounded work.

## Stop conditions

Stop only for an unclear owner outcome, active branch/path/domain collision,
identity/privacy/authorization issue, unsafe migration or deletion, conflict
between current authorities, missing locked material-visual authority, or a
failed executable gate. Old packages and unrelated findings are not stops.

Stop when the authorized outcome and required checks are complete. Repeat checks
only for changed inputs, failures or unresolved requirements.
