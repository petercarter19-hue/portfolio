# PeerSlate worktree lifecycle

This standard controls local PeerSlate worktrees after the
`PS-WORKTREE-LIFECYCLE-001` bootstrap. Azure `origin/main`, the active package
claim, and `delivery_preflight.py` remain repository authority. The local
registry is operational inventory; it never grants repository or production
authority.

## Default topology

- Each active package has at most one durable full worktree. Its assigned
  writers reuse that exact checkout instead of creating one per model, review,
  control step, or session.
- Review is Azure- or pushed-diff-first and creates no worktree. A reviewer may
  inspect the package worktree read-only only when coordinated with its writer
  and there is no concurrent mutation. Runnable isolation is exceptional.
- One permanent sparse workspace at the deterministic managed path `_control`
  is shared by all packages. A cross-process mutex and one task lease make its
  `control` and `verify` modes mutually exclusive. It is repointed only while
  pristine; the same task releases its clean lease and retains the singleton
  for reuse.
- Ad hoc `git worktree add` is prohibited. Use
  `scripts/worktree_lifecycle.py`; never work around a refusal by creating
  another checkout.
- Caches, scratch files, and generated outputs stay outside worktrees. Follow
  [Evidence retention and deduplication](EVIDENCE_RETENTION_AND_DEDUPLICATION.md)
  for repository-canonical proof and external custody.

The sparse singleton includes the root control files, `docs/governance/`,
`scripts/`, focused tests, claimed paths needed by the operation, and explicit
verification includes. It is not a second durable package worktree.

## Registry and transaction model

The tool stores `peerslate/worktree_registry.json` under the resolved Git
common directory. That machine-local file records the policy activation,
managed root, external evidence root, durable package worktrees, the `_control`
singleton, exceptional task-temporary worktrees, task leases, pending
operations, and grandfathered observations.

Registry changes use an exclusive lock directory, write a pending operation
before Git mutation, and publish JSON through a temporary file plus
`os.replace`. Every mutation reconciles the exact filesystem path and
`git worktree list --porcelain -z` before closing the operation. `audit` is
read-only: it reports drift, collisions, stale operations, and post-policy
unregistered growth; it never adopts, repairs, prunes, or removes anything.

A hard process death can leave the lock directory behind. The tool does not
guess that such a lock is stale or break it automatically; later mutation
fails closed until the recorded owner and exact local state are investigated.

```powershell
python scripts/worktree_lifecycle.py audit --json
```

Commands normally run from a PeerSlate worktree. When discovery needs an
explicit checkout, put the optional global `--repo <absolute-path>` before the
subcommand.

Task references are opaque coordination identifiers, for example
`session:<task-id>`. They do not identify a person or confer authority.

## Commands

Registry and lifecycle mutation commands require `--execute`; without it they
do not change a worktree or registry. Runtime `verify` is the narrow exception:
`--runtime-required` plus its trailing command is the explicit action. Use the
same exact `--task-ref` throughout one task. Commands emit JSON; a guarded
refusal exits with code 2.

### Initialize and grandfather

Run `init` once per local Git common directory. It records every worktree that
already exists as a `grandfathered_observation`, records the activation
boundary, validates an external evidence root outside all worktrees, and
recognizes the deterministic sparse `_control` singleton. Grandfathering is
observation only: it does not approve, adopt, repoint, clean, or delete a
checkout.

```powershell
python scripts/worktree_lifecycle.py init --task-ref "session:<task-id>" --evidence-root "X:\CodexData\maintenance\evidence" --execute
```

There is intentionally no separate bulk-grandfather or bulk-adopt action.

### Adopt or ensure one durable package worktree

`adopt` adds bookkeeping for one exact existing non-primary worktree. It
requires the fetched active claim, exact claim branch and writer task
reference, the same Git common directory, and no duplicate package, branch, or
path. Adoption never changes files, branch, or HEAD; a dirty active writer
checkout may be adopted to preserve its work.

An exact worktree observed and grandfathered by `init` may be adopted in place
even when it predates the managed root. The record marks that legacy boundary;
`ensure` reuses it, while guarded retirement preserves it because removal is
restricted to the managed root. A newly unregistered outside-root path cannot
be adopted.

```powershell
python scripts/worktree_lifecycle.py adopt --package "PS-EXAMPLE-001" --path "C:\Users\peter\Documents\PeerSlateWorktrees\PS-EXAMPLE-001" --task-ref "session:<writer-task-id>" --execute
```

`ensure` idempotently returns that registered durable worktree or creates the
one deterministic full worktree allowed by the active claim. It refuses a
paused, closed, missing, mismatched, colliding, or already-present branch. If a
grandfathered checkout already carries the branch, use exact `adopt`; do not
make a duplicate.

```powershell
python scripts/worktree_lifecycle.py ensure --package "PS-EXAMPLE-001" --task-ref "session:<writer-task-id>" --execute
```

### Lease `_control` for a claim transition

Activation, authorize, transfer, pause, resume, close, and the
owner-authorized evidence-errata amendment of a closed package's fixed
evidence file all reuse `_control`; for evidence-errata the lease names the
closed package and the claim itself is never edited.
`control` acquires the singleton lease, proves it pristine, and repoints it to
the requested dedicated control branch and base. Run the one-claim transition
there, then finalize it in the same task.

```powershell
python scripts/worktree_lifecycle.py control --package "PS-EXAMPLE-001" --task-ref "session:<task-id>" --branch "work/2026-08-23-delivery-close-example-001" --base "origin/main" --execute
python scripts/worktree_lifecycle.py finalize-task --task-ref "session:<task-id>" --execute
```

`finalize-task` releases only that task's clean lease, leaves `_control`
pristine at its current branch/SHA for the next guarded repoint, and retires
only that task's clean managed ephemeral verifiers. It reports and preserves
any residue, mismatch, or ambiguity. It never retires a durable package
worktree or another task's resource.

### Run isolated verification only when necessary

The normal reviewer reads the immutable Azure/pushed diff. The optional
diff-only check below validates that the candidate is exact and durably
reachable and reports `worktrees_created: 0`:

```powershell
python scripts/worktree_lifecycle.py verify --package "PS-EXAMPLE-001" --candidate-sha "<40-character-sha>" --task-ref "session:<review-task-id>"
```

When execution isolation is genuinely required, `verify` requires explicit
`--runtime-required` and the narrow include set. It leases the same `_control`
singleton in detached sparse mode; a control lease or another task's
verification lease blocks it.

```powershell
python scripts/worktree_lifecycle.py verify --package "PS-EXAMPLE-001" --candidate-sha "<40-character-sha>" --task-ref "session:<review-task-id>" --runtime-required --include "tests/test_example.py" -- python -B -m unittest tests.test_example -q
```

On clean success the singleton is retained for reuse, not copied or deleted.
`--ephemeral` is an exceptional escape hatch. A successful pristine ephemeral
is ordinarily retired in the same command; a failed run or any tracked,
untracked, or ignored residue is preserved at its exact path for the creating
task to resolve and retire or report. While its command is running, a unique
invocation lease blocks direct retirement, finalization, and a second verifier
from touching that path. A process death leaves that lease fail-closed for
explicit investigation; it never authorizes guessed cleanup.

### Allocate generated-evidence storage

`evidence-path` returns a deterministic location and records budget, storage
class, retention reason, close condition, and projected full-worktree
replication cost. External roots must remain outside every worktree.

```powershell
python scripts/worktree_lifecycle.py evidence-path --package "PS-EXAMPLE-001" --task-ref "session:<task-id>" --storage-class "x_maintenance" --byte-budget 250000000 --label "browser-proof" --execute
```

Valid storage classes are `repo_canonical`, `azure_artifact`,
`x_maintenance`, and `ephemeral_same_task`. The evidence standard controls
hash manifests, retention, recovery ownership, and what may remain in Git.

### Retire an exact managed worktree

Use `retire` only for an exact registered managed path. A temporary worktree
may be retired only by its creating task. A durable package worktree also
requires a fetched closed claim and a recoverable exact branch/HEAD.

```powershell
python scripts/worktree_lifecycle.py retire --path "C:\Users\peter\Documents\PeerSlateWorktrees\PS-EXAMPLE-001" --task-ref "session:<writer-task-id>" --expected-head "<40-character-sha>" --execute
```

## Non-negotiable retirement refusals

The tool preserves the worktree and exits with a refusal when any check is
uncertain or fails. In particular, it refuses:

- an unregistered, non-canonical, moved, primary, broad, home/root, outside-
  managed-root, reparse-point, nested-worktree, or invoking-process CWD target;
- a common-directory, registry kind, task lease, package, branch, or exact
  HEAD mismatch;
- any tracked change, untracked file, **or ignored file**;
- a commit that is not the exact server-confirmed tip of the package's claimed
  branch; stale local remote-tracking refs and local-only tags are never
  recovery proof;
- a durable package whose fetched claim is not closed; or
- any duplicate, stale pending operation, collision, or ambiguous state.

After all gates pass, retirement invokes only ordinary non-force
`git worktree remove <exact-path>` and then proves that the exact path is gone
from both the filesystem and Git's registry. The lifecycle tool has no path
that force-removes, recursively deletes, deletes a branch/tag/ref, prunes,
runs garbage collection, resets, or cleans.

The standard-library guard can prove that its own process CWD is outside the
target; it cannot portably enumerate every other Windows process CWD. If
another process keeps the target live, ordinary non-force Git removal must
fail, the target is preserved, and the pending operation is reconciled as
preserved on the next mutation.

## Local enforcement boundary

On an initialized developer machine, mutating delivery preflights require the
exact managed context: `write` and `merge` use the package's durable worktree;
control intents use the leased `_control` singleton. A post-policy
unregistered mutating workspace fails. An unrelated grandfathered worktree
never becomes a global blocker; only an exact branch, path, domain, lease, or
safety collision blocks the colliding work.

CI and a machine with no initialized registry remain valid and receive a
warning rather than a local-registry failure. `read` remains read-only and
worktree-free. These local checks supplement claim and Azure authority; they
do not replace either.

## Bootstrap, transition, and honest limit

The package itself used one manually created sparse control workspace because
the guard did not yet exist. After the tool passes, `init` registers that same
workspace as the permanent `_control` singleton and grandfathers every other
then-existing worktree without changing it. Only an exact current active-
package checkout may later be adopted. This transition authorizes no legacy
cleanup, bulk adoption, evidence migration, branch/ref removal, deployment,
schema/configuration change, or production action.

Repository instructions cannot stop Codex or another host from creating a
project worktree before those instructions load. Start review tasks
projectless or from Azure/pushed diffs where possible, then use `audit` to flag
any new unregistered host-created worktree immediately. The lifecycle cannot
truthfully promise that such pre-instruction creation never occurs; it makes
the growth visible and prevents that checkout from becoming an accepted local
mutation lane.
