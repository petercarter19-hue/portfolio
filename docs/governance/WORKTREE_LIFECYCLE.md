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

Closed-custody retirement has its own `retire_closed_custody` journal. It binds
one exact active source record to one exact retired successor record plus the
cleanup package/writer/worktree/branch/HEAD, owner authorization, distinct
source-unavailability evidence, original package/task/path/branch, previous
registry HEAD, expected/server HEAD, authoritative main, and timestamp. The
registry keeps the active before-record until ordinary Git removal succeeds.
Recovery clears the journal as preserved only when the exact worktree still
exists in both filesystem and Git and its managed/reparse-safe path,
repository, branch, live/local HEAD, nesting, and pristine state still match
the immutable proof, or publishes the exact after-record only when it is
absent from both. A mismatch retains the journal and refuses. The proof's
previous registry HEAD must equal the journal's exact before-record HEAD.

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

After a merged owner-reassignment claim, `ensure` additionally proves both
preserved remote branches at the recorded checkpoint. If the old durable
worktree exists and is pristine at that checkpoint, the registry preserves it
as a non-writable `reassignment_source` and creates the receiver's durable
checkout at a deterministic recovery path. It does not switch, reset, remove,
or otherwise mutate the source checkout. A missing merge, malformed handoff,
moved branch, or dirty source is a refusal.

```powershell
python scripts/worktree_lifecycle.py ensure --package "PS-EXAMPLE-001" --task-ref "session:<writer-task-id>" --execute
```

### Lease `_control` for a claim transition

Activation, authorize, active-claim surface extension, transfer, owner
reassignment, pause, resume, close, and the
owner-authorized evidence-errata amendment of a closed package's fixed
evidence file all reuse `_control`; for evidence-errata the lease names the
closed package and the claim itself is never edited.
`control` acquires the singleton lease, proves it pristine, and repoints it to
the requested dedicated control branch and base. Run the one-claim transition
there, then finalize it in the same task.

For ordinary `close`, the merged receipt must identify a reviewed candidate
with at least one non-evidence claimed surface introduced by `merged_sha`.
An arbitrary empty candidate or evidence-only audit still cannot close.

An operations-only closed-custody cleanup has one narrow alternative. First
merge its independently reviewed lifecycle mechanism and receipt, then perform
only admitted `retire-closed-custody` operations from its active durable
worktree. Synchronize that branch with accepted main. Copy **all** of this
package's completed `closed_custody_retirement` proof objects from the local
registry into its fixed evidence file, inside exactly one fenced block:

````text
```peerslate-closed-custody-completion
{"schema_version": 1, "package": "<CLEANUP-PACKAGE>", "retirements": [<exact completed proof objects>]}
```
````

Freeze and push that evidence-only completion candidate. Obtain an independent
review of the exact completion evidence and custody (not a duplicate code
review), update the package receipt to that candidate, and merge. Do not change
the evidence after review. Close against the commit that introduced that
evidence, using the ordinary leased `delivery-close` transition. Do not invent
an unrelated code or documentation change just to satisfy close.

The exception requires the originating initialized machine registry, even in
CI; CI or a missing registry cannot attest local operations completion. It
reads custody under the registry mutex and refuses pending state, empty or
omitted operations, duplicate custody, or any mismatch with completed retired
records and the current cleanup writer, owner, branch and durable worktree.
Every original target must remain closed, absent from filesystem and Git, and
recoverable at its exact current server branch tip. Each operation must carry
its accepted historical independent mechanism review, distinct target-specific
source-unavailability reference and original writer custody. The reviewed
lifecycle surfaces, plus `delivery_preflight.py` and its tests, must be
byte-identical at the mechanism candidate, operation authority/cleanup HEAD,
completion candidate, merge, current main and preserved cleanup branch.
Completion evidence must be identical at candidate/merge/main/branch, and its
receipt identical at merge/main/branch. This is a close-only proof check; it
does not retire anything, reconcile a registry or extend cleanup authority.

```powershell
python scripts/worktree_lifecycle.py control --package "PS-EXAMPLE-001" --task-ref "session:<task-id>" --branch "work/2026-08-23-delivery-close-example-001" --base "origin/main" --execute
python scripts/worktree_lifecycle.py finalize-task --task-ref "session:<task-id>" --execute
```

`finalize-task` releases only that task's clean lease, leaves `_control`
pristine at its current branch/SHA for the next guarded repoint, and retires
only that task's clean managed ephemeral verifiers. It reports and preserves
any residue, mismatch, or ambiguity. It never retires a durable package
worktree or another task's resource.

### Prepare an owner-reassignment successor

Owner reassignment is a Protected recovery distinct from voluntary transfer.
It requires Pete's exact opaque authorization reference and a leased pristine
`_control` singleton on a current-main
`work/YYYY-MM-DD-delivery-owner-reassignment-<slug>` branch. Run this before
editing the claim:

```powershell
python scripts/worktree_lifecycle.py prepare-owner-reassignment --package "PS-EXAMPLE-001" --task-ref "agent:<receiving-writer>" --successor-branch "work/2026-08-27-example-recovery" --expected-checkpoint "<40-character-old-remote-sha>" --owner-authorization-ref "session:<owner-decision>" --execute
```

If bounded orchestrator/lifecycle evidence proves the source task is no longer
available, but its exact managed durable checkout and server branch advanced
identically beyond the registry's recorded HEAD, add
`--source-unavailable-ref "session:<bounded-evidence>"`. This does not let the
receiver act as the old task. The exception is admitted only inside successor
preparation and requires the active claim's exact package, old writer, branch,
and canonical path; no lease, lock, pending operation, duplicate, residue, or
ambiguity; a pristine source checkout; equal live HEAD, local branch, and exact
fetched server tip; and an old recorded HEAD that is a Git ancestor of the
requested checkpoint. The tool records the owner and unavailability references
in machine-local custody evidence.

The command requires a complete initialized registry with exactly one
`control_singleton` record: that record must be active, receiver-leased,
current-main, pristine, and at the deterministic `_control` path, with no
competing lock or unresolved pending operation. Every preparation record and
legal transient state is schema-validated before recovery, journaling, or
remote mutation; a duplicate control, poisoned history, or orphan transition
stops. A registry worktree marked `pending` must have one exact matching create
journal; every create, retire, closed-custody-retire, control-repoint, and
branch-create journal must
also have its exact field set, timestamp, canonical path where applicable, and
registry-record/control custody before reconciliation. Invalid journals and
orphan or ambiguous pending records stop without changing the registry. The control branch must
fully match the owner-reassignment intent and
must differ from the old branch. It exact-fetches and rechecks the old remote
branch. Before writing its journal or pushing, it reconciles every
active durable record selected by the target package or source branch against
one exact canonical absolute path in live Git, the old task reference, old
branch, checkpoint HEAD, and pristine tracked/untracked/ignored state. Missing,
detached, switched, moved, dirty, duplicate, or ambiguous records refuse before
remote creation.

The successor must be normalized and distinct, unclaimed and server-absent,
with no exact or ancestor/descendant namespace collision across local heads,
origin-tracking refs, live claims, live worktrees, or active registry branch/
source-branch custody. The tool journals the operation before mutation, uses an
empty-expectation lease as an absent-ref compare-and-set, requires Git's exact
`[new branch]` response, and immediately fetches and proves the successor at
the same SHA. Its final proof rechecks the old branch, source worktrees, current
server main, strict live claims, and branch namespaces. Normal completion and
crash recovery share one final helper that repeats the exact server successor,
old branch, main, and claim proof immediately before appending `completed` and
clearing the journal. This is creation-only:
the lease cannot overwrite an existing ref, and the command creates no local
successor branch and never mutates the old branch or worktree.

If the process stops before server creation, reconciliation first proves the
successor remains absent and clears the unproven pending record without letting
later old-tip movement turn a never-started push into ambiguity. If creation is
proven, reconciliation completes only when both remote refs, prepared main,
strict live claims, every recorded source checkout, and every source durable
record still have their exact identities. A successor ref without a recorded
exact `[new branch]` response is ambiguous and remains fail-closed for
investigation; the tool never guesses ownership, deletes the ref, or retries
with force.

Successful completion atomically clears the pending journal and appends one
`completed` preparation tuple. Its digest-bound immutable fields are package,
owner authorization, old/new task refs and branches, checkpoint, control
branch, prepared main, proof timestamp, the exact new-branch response, and the
source snapshot (local source ref, source worktrees, and reconciled durable
records). When active-durable HEAD recovery is used, the immutable tuple also
contains the exact `source_head_reconciliation` proof, including its separate
source-unavailability reference. Schema-1 registries created before this field existed load it as an
empty list and persist it on the next lifecycle mutation; no registry reset or
re-initialization is required. Once present, every record must have the exact
`completed`, linked `consuming`, or terminal `consumed` field set, type-exact
references and SHAs, unique digest and handoff identity, normalized source
snapshot, and legal package state. Malformed, duplicated, replayed, or incompatible history is never
silently discarded.

When that guarded active-durable HEAD exception is used, the stale-record
correction and the successor-creation journal are published together. If the
successor remains absent, recovery restores the complete prior durable record
and clears the journal in one write. If Git supplies the one exact
`[new branch]` proof, final recovery repeats ancestry, source, claim, namespace,
and server-tuple checks before committing the reconciled custody record and
completed preparation together. A missing proof or any race preserves the
journal and refuses. Every proof-bearing custody record must link in both
directions to exactly one current branch-create journal or digest-valid
completed/consuming/consumed preparation; an omitted journal field, orphan
proof, or changed reference fails before recovery. No branch is moved or
deleted. Governed `superseded`
claims are terminal records and are excluded from live ownership.

After preparation, change only the claim's `writer_ref`, `branch`, and exact
`owner_reassignment` handoff and validate with the matching delivery intent.
That intent requires this machine's initialized registry, one exact active
receiver-leased `_control` singleton, no lock or pending ambiguity, and one
digest-valid `completed` tuple matching the claim, control branch, current
main, exact server response, and a twice-stable live source snapshot. It rejects
CI/uninitialized bypass, successor namespace changes, mismatches, source
mutation, duplicates, and a tuple already marked `consumed`. Immediately before
admission—after all owner-specific claim, source, namespace, and remote
work—it acquires the lifecycle registry mutex, requires the registry to equal
its earlier validated snapshot, and repeats the exact lease, absent pending
state, preparation history, live source, namespace, main, claims, old-branch,
and successor proofs before its final reread and mutex release. A mutation
after an earlier proof therefore fails closed.

Finalizing a lease or repointing `_control` leaves every completed preparation
field unchanged. If main later advances, preflight may reuse that preparation
only from a distinct fresh owner-reassignment control branch based on current
main, only when prepared main is its strict ancestor and the target claim's
exact ordinary Git blob is byte-identical at both commits. The preparation
digest, exact `[new branch]` response, source snapshot, lease, namespace,
claims, and remote tuple proofs remain mandatory and repeat under the terminal
mutex. Local source-head discovery uses exact `for-each-ref` enumeration: no
exact entry means absent, while command failure, malformed or duplicate output,
or an exact non-commit ref refuses. This continuity path never edits the
preparation, creates or moves a ref, or relaxes post-merge consumption.

The receiving writer cannot use `ensure` or write preflight until that control
PR merges to `origin/main`. On the first post-merge `ensure`, the tool rechecks
the exact preparation and source state, preserves the old durable checkout as
`reassignment_source`, creates the distinct receiver durable worktree, and
changes the tuple to `consumed` in the same registry commit as that creation.
Its transient `consuming` state is valid only inside that pending create
journal: reconciliation restores `completed` when no receiver worktree exists,
or atomically finishes `consumed` only for the exact created worktree and
unchanged source snapshot. The receiver worktree must also be pristine,
including tracked, untracked, and ignored files. Any residue retains both the
`consuming` proof and pending journal for investigation; it never activates the
receiver or marks the proof consumed.
Consumed proof cannot authorize another control transition; later `ensure`
calls revalidate the consumed proof and exact preserved source custody, then
may reuse and normally advance the successor branch while leaving the old
source and immutable reassignment provenance intact. The old branch and
preserved source worktree remain outside receiver cleanup authority.
A later authorized reassignment keeps all older `reassignment_source` records
and consumed tuples under their own preparation handoffs, while matching and
preserving only the current preparation's durable source for the new receiver.

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

### Retire closed custody when the original task is unavailable

`retire-closed-custody` is a distinct owner-authorized Protected path. It is
not a transfer, does not make the cleanup writer the source writer, and cannot
retire an active or paused claim. It also cannot run from an unreviewed or
unmerged implementation: fetched main must contain an exact independent-pass
receipt and its evidence, every reviewed lifecycle surface must match the
candidate on both main and the cleanup branch, and the executing lifecycle
script blob must equal that reviewed main blob. Run it only from the exact active
durable worktree of the cleanup package after the reviewed mechanism is merged:

```powershell
python scripts/worktree_lifecycle.py retire-closed-custody --cleanup-package "PS-WORKTREE-LIFECYCLE-CLOSED-CUSTODY-001" --task-ref "agent:<cleanup-writer>" --target-package "PS-CLOSED-EXAMPLE-001" --path "C:\Users\peter\Documents\PeerSlateWorktrees\PS-CLOSED-EXAMPLE-001" --branch "work/YYYY-MM-DD-closed-example-001" --source-task-ref "session:<original-writer>" --expected-head "<40-character-server-sha>" --owner-authorization-ref "session:<owner-cleanup-decision>" --source-unavailable-ref "session:<target-specific-unavailability-proof>" --execute
```

The cleanup claim must be current on fetched `origin/main`, active,
`Protected`, `implementation`, `through_merge`, production-withheld, and
independently reviewed, with the exact lifecycle cleanup surfaces/domains,
writer, branch, and owner reference. Its canonical durable worktree must be the
invoking CWD; the registry identity, pristine live checkout, local branch, and
server tip must agree exactly. The target claim must be fetched and exactly
`closed`, with its original writer and branch equal to the explicit arguments.
The target must be one canonical active managed durable record and one live Git
worktree, with no lease, duplicate package/branch/path custody, nested
worktree, reparse point, residue, or ambiguity. Live HEAD, the local branch,
and the server branch must all equal `--expected-head`. The registry HEAD may
equal that commit or be its proven ancestor; missing, ahead, or divergent
registry custody refuses.

Immediately before journaling, one server advertisement re-proves current
main, the cleanup branch, and the target branch while the registry mutex is
held. The source-unavailability reference must be different from the cleanup
caller, original task, and owner reference, and it may appear in only one
completed or pending closed-custody operation. The journal records immutable
before/after snapshots. Completion leaves the retired record's `task_ref` set
to the original task and records the cleanup caller separately in
`closed_custody_retirement`. It then invokes the same sole ordinary non-force
Git removal helper as `retire`. It never resets, cleans, force-removes, prunes,
runs garbage collection, or deletes/moves a branch, tag, or ref.

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
control intents, including owner reassignment, use the leased `_control`
singleton. A post-policy
unregistered mutating workspace fails. An unrelated grandfathered worktree
never becomes a global blocker; only an exact branch, path, domain, lease, or
safety collision blocks the colliding work.

CI and a machine with no initialized registry normally remain valid and receive
a warning rather than a local-registry failure. Owner reassignment is the
narrow exception because its exact server-creation/source proof exists only in
the machine-local registry: that control intent rejects CI or uninitialized
execution. `read` remains read-only and worktree-free. These local checks
supplement claim and Azure authority; they do not replace either.

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
