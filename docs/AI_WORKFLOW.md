# PeerSlate Lean Delivery Workflow

_One writer per mutable surface; unlimited disjoint work; explicit production
operations._

## Default flow

Equivalent assignments keep the same lifecycle across runtimes; coordination
grants no exclusive privilege. Preserve actual caller identity and reviewed
acceptance.
`docs/governance/WORKTREE_LIFECYCLE.md` governs lost-task custody recovery;
`START_HERE.md` governs required-check repair admission, retaining Azure CI and
branch policies. Configuration does not prove access.

1. Follow `START_HERE.md`, fetch Azure main, preserve unrelated work, and read
   the current package claim.
2. Choose Routine, Bounded, or Protected. On an initialized developer machine,
   reuse the package's one registered durable worktree and pass its exact
   writer `--task-ref` to mutating preflight. `ensure` includes
   non-gating read-only readiness.
3. The assigned writer implements, validates, self-reviews the complete diff,
   corrects findings, opens the PR, and merges accepted work.
4. Add an independent exact-SHA review only when Protected risk, the package,
   or Pete requires it. The reviewer is read-only, consumes no writer claim,
   and defaults to the Azure/pushed diff without creating a worktree.
5. Report merge, deployment, schema, enablement, and live verification as
   separate states.

Specialist reviews and audits are event-driven; none is required
unless its delivery path or package specifically triggers it. Use
[capability routing](AI_MODEL_AND_ROLE_ROUTING.md#capability-use) for model and tool choices.

## Concurrency and collision rule

Writers may proceed without capacity limits on unique branches and disjoint
normalized paths and hierarchical domains.
Review-only tasks claim no mutable surfaces.

Each package permanently owns its claim, receipt and evidence paths; other
claims cannot reserve them or a broad parent. Paused work releases product
paths/domains but reserves its branch. Closed work releases implementation
ownership, not its historical control namespace.

Collisions stop only affected packages. Disjoint main movement preserves review;
movement across a claimed surface expires it.

## Worktree lifecycle

Ad hoc `git worktree add` is unsupported. Active packages reuse one durable
worktree through `ensure` or exact `adopt`. Reviews create none. Claim
transitions and necessary runnable verification share the mutex- and
task-leased sparse `_control` singleton; the same task finalizes temporary
resources.

The local registry never grants repository authority. Once initialized, it
blocks only an unregistered mutating workspace; CI, missing registry, and
unrelated grandfathered worktrees remain non-blocking. `audit` is read-only.
Retirement uses exact registered paths and ordinary non-force Git removal after
the checks in `docs/governance/WORKTREE_LIFECYCLE.md`.

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

For current claims, run merge preflight in the clean durable worktree with
`--task-ref <WRITER-REF>`; create no verifier.

For candidates predating generic claims, use the current-main script in a clean
verifier with `--candidate-worktree <FROZEN-WORKTREE>`. Preserve the old branch
bytes; current `origin/main` supplies authority.

```bash
python scripts/delivery_preflight.py --package <PACKAGE-ID> --intent merge --candidate-sha <REVIEWED-SHA> --candidate-worktree <FROZEN-WORKTREE> --fetch --require-clean
```

### Documentation-only closeout

For bookkeeping that is not runtime-consumed, merge with `[skip ci]` in the
final squash message. Do not restart App Service merely to publish bookkeeping.

## Production boundary

Automatic main and PR runs are CI-only. Production web deployment is a manual
operation requiring an exact 40-character main SHA and Pete's explicit
authorization reference. Schema actions remain manual, separately checked, and
mutually exclusive with a web deployment. Azure environment locks serialize
production operations across runs.

Do not queue a deployment because CI is slow. Do not claim a merge is live.
Before any separately authorized production operation, confirm its exact source
SHA, requested action, authorization reference, active locks, rollback/disable
path, and evidence. Afterward verify exact release identity and the affected
journey before reporting live.

## Handoffs and closeout

Use `MANAGER_SESSION_HANDOFF.md` only when ownership actually changes. Package,
branch, pushed SHA, opaque task references, relinquishment, scope, evidence, and
next action are sufficient; no real-world identity disclosure is required.

Pause only at an exact pushed checkpoint. Resume through the one-claim
`delivery-resume` transition; it changes only paused to active, proves the
fetched checkpoint, and reruns collisions. Preserve the remote implementation
branch through close so squash-merge byte proof remains reproducible. If it was
deleted, re-push the exact reviewed branch before retrying close.

Record outcome, SHAs, changes, tests, review, release states, limits, next
action, and exact-session `finalize-task` usage or unavailable once. Candidate,
Launch, Operate, Retire, visual acceptance, and full-site audits are
event-driven. None blocks unrelated Routine or Bounded work.

## Stop conditions

Stop only for an unclear owner outcome, active branch/path/domain collision,
identity/privacy/authorization issue, unsafe migration or deletion, conflict
between current authorities, missing locked material-visual authority, or a
failed executable gate. Old packages and unrelated findings are not stops.

Stop when the authorized outcome and required checks are complete. Repeat checks
only for changed inputs, failures or unresolved requirements.
