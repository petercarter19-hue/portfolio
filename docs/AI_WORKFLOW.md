# PeerSlate Lean Delivery Workflow

_One writer per mutable surface; unlimited disjoint work; explicit production
operations._

## Default flow

1. Follow `START_HERE.md`, fetch Azure main, preserve unrelated work, and read
   the current package claim.
2. Choose Routine, Bounded, or Protected. On an initialized developer machine,
   reuse the package's one registered durable worktree and pass its exact
   writer `--task-ref` to mutating preflight.
3. The assigned implementation writer completes the scoped repository work:
   implementation, focused validation, complete-diff self-review, review
   correction, PR, and accepted merge.
4. Add an independent exact-SHA review only when Protected risk, the package,
   or Pete requires it. The reviewer is read-only, consumes no writer claim,
   and defaults to the Azure/pushed diff without creating a worktree.
5. Report merge, deployment, schema, enablement, and live verification as
   separate states.

No architecture pass, manager handoff, independent review, Candidate
environment, specialist-document sweep, or full-site audit is universal. None
is required unless its delivery path or package specifically triggers it.

## Concurrency and collision rule

Any number of implementation writers may proceed when every active claim has a
unique work branch, non-overlapping normalized paths, and non-overlapping
hierarchical domains. There are no fixed writer, lane-class, shared-foundation,
direction, or production-capable counts. Review-only tasks do not claim mutable
surfaces.

Each package permanently owns its exact claim, receipt, and evidence paths;
ordinary claims may not reserve another package's control records or a broad
parent. Paused work releases product paths/domains but keeps its branch reserved
until resume or close. Closed work releases implementation ownership, not its
historical control namespace.

A collision is a stop for the colliding packages only. Disjoint main movement
does not expire a reviewed candidate. Movement across one of its claimed
surfaces does.

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

Every merge freezes and pushes one exact candidate and records a receipt.
Routine and Bounded writers complete self-review and issue a `self` receipt
whose opaque reviewer reference equals their writer reference. Protected work
uses the required read-only independent reviewer. Correct findings and freeze
again until one exact candidate passes. The writer may then add only the
generic review receipt and fixed runtime-inert
`lane_claims/evidence/<PACKAGE-ID>.md`. Merge preflight verifies the reviewed
SHA, receipt, remote branch tip, claimed paths, evidence-only tail, and
non-colliding main movement.

An explicitly narrowed `write_only` claim cannot merge. If Pete later expands
that exact assignment, a `delivery-authorize` control PR may change only
`repository_authority` from `write_only` to `through_merge` and replace
`owner_outcome_ref` with the new opaque decision reference. Validate it with
`--intent authorize`, merge the control PR, and then use the ordinary review
and merge path. This transition is not needed for normal implementation claims.

Use an Azure PR. Current-target CI and unresolved comments still apply. A green
PR or a merge is repository truth, not deployment truth.

For a current claim, run merge preflight in its clean durable implementation
worktree and pass `--task-ref <WRITER-REF>`; do not create a verifier checkout.

If a frozen candidate predates generic claims, use the current-main script from
a clean verifier with `--candidate-worktree <FROZEN-WORKTREE>`; the old branch
stays byte-for-byte unchanged while current `origin/main` supplies authority.

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

Use one proportional completion record. Core evidence is outcome, base/final
SHA, changed paths, tests, review, PR/merge state, deployment state, honest
limit, and next action. Candidate, Launch, Operate, Retire, visual acceptance,
and full-site audits are event-driven. None blocks unrelated Routine or Bounded work.

## Stop conditions

Stop only for an unclear owner outcome, active branch/path/domain collision,
identity/privacy/authorization issue, unsafe migration or deletion, conflict
between current authorities, missing locked material-visual authority, or a
failed executable gate. Old packages and unrelated findings are not stops.
