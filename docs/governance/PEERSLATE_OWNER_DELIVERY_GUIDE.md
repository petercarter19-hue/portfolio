# Pete's PeerSlate delivery guide

This is the plain-English operating guide for enjoying broad product discovery
without turning every good idea into simultaneous production work.

## The one rule that matters most

**Ideas can be unlimited. Active implementation cannot be.**

Talking through a feature, requesting feedback, creating a visual direction,
or saving a future idea does not need a branch, worktree, package activation,
database change, PR, or deployment. Those begin only when Pete deliberately
chooses the next outcome to build.

## The five-step rhythm

1. **Explore.** Discuss, research, sketch, or compare possibilities. Keep it
   read-only. Say: “Discovery only; do not create a branch or change anything.”
2. **Choose.** Name one outcome, what is excluded, and whether it is allowed to
   become the next implementation lane.
3. **Build.** Assign one manager only when needed and exactly one writer for
   each mutable surface. Use one current branch/worktree from Azure `main`.
4. **Verify.** Separate tests, review, owner acceptance, PR, merge, deployment,
   and live verification. None of those words means all the others.
5. **Close.** Record the final SHA/state, delete or archive the finished branch
   and worktree after evidence is preserved, then release the next lane.

## Work-in-progress limits

| Kind | Limit | Meaning |
|---|---:|---|
| Production-capable lane | 1 | The only lane allowed to merge toward production or touch a protected operation. |
| Implementation lanes | 2 total | They must have non-overlapping files and only one may be production-capable. |
| Product/visual discovery lane | 1 | Discussion and authority creation only; no runtime branch until activated. |
| Ideas and future possibilities | Unlimited | Capture them without activating implementation. |

When the limit is full, a new idea is not rejected. It waits until Pete closes
or explicitly pauses one current lane.

## Which delivery path applies?

### Routine

Use for copy, a small isolated bug, a focused test, documentation, or an
established-component correction. It needs one writer, focused validation, and
one complete-diff self-review. It does not need a new architecture, visual
round, independent reviewer, Candidate environment, or full-site audit.

### Bounded

Use for an approved feature or route inside an established package and
architecture. It needs the brief, focused contract tests, self-review, and the
ordinary PR/pipeline/live sequence if released.

### Protected

Use only when the change touches identity, authorization, privacy, canonical
data, migration, deletion/publication, consequential AI, shared
infrastructure/configuration, major availability risk, or materially revised
visual direction. It adds the exact risk-specific evidence and independent
review the package calls for.

Do not promote Routine work into Protected ceremony merely because the
repository has historical Protected packages.

## Gate cheat sheet

| Gate | Pete's decision | What must be true before it advances |
|---|---|---|
| Discovery | “Advice/visual exploration only.” | No implementation or release claim. |
| Activation | “Build this exact outcome next.” | Current Azure base, one writer, bounded scope, direct dependencies ready. |
| Visual lock | “This exact concept is the authority.” | Needed only for new or materially revised production visual direction. |
| Data/schema | “This protected change may enter its gate.” | New immutable migration ID, actual-target inventory, proof, rollback, hosted identity path. |
| Owner acceptance | “The implemented result is accepted.” | Tests/review evidence and honest limitations are visible. |
| Merge | “This accepted SHA may enter main.” | Current-target Azure policy passes; comments resolved; no other production reservation. |
| Deployment | Automatic main run is selected. | Do not queue a fallback while it exists or is merely slow to appear. |
| Live | “Exact build and affected journey verified.” | Release identity, routes/contracts, alerts, cleanup, and schema state when applicable. |
| Close | “This lane is finished.” | Completion record, branch/worktree disposition, ownership released. |

For a direction-only package, those gates are executable and separate. The
grant points back to a Pete decision that already authorizes merge and locks
the reviewed pushed SHA; it does not manufacture new approval. Merge accepts
only that SHA and only non-overlapping main movement. Close proves the package
tree reached current main, removes every authority entry, and preserves an
inert historical record. Runtime, deployment, release, schema, and production
rights remain outside this path.

If the reviewed package has older control code, it stays frozen. A separate
clean verifier at current Azure `main` runs the merge check against the
candidate's absolute registered worktree path. The two worktrees must belong
to the same repository and Azure origin; changing, rebasing, overlaying, or
detaching the candidate is a stop. Complete the direction PR with automatic
source-branch deletion disabled: exact close revalidates that remote tip.
Retain it through close, then remove it only under the recorded cleanup path.

## Copy-paste directions for Pete

### Explore an idea without opening work

> Discovery only. Give me advice, risks, options, and a recommendation. Do not
> create a package, branch, worktree, code change, PR, pipeline, deployment, or
> production change. Tell me what existing active lane this would compete with.

### Activate one implementation

> Make this the next implementation outcome: [one sentence]. Everything else
> discussed is parked. Verify current Azure main and CURRENT_LANES first. Use
> the small delivery-activation record to name the package, writer, future
> implementation branch, writable files, exclusions, delivery path, and exact
> completion evidence. Merge that record before creating the implementation
> worktree. Put no product code in the activation branch.

### Pause a lane safely

> Stop before the next write, merge, deployment, or schema operation. Preserve
> all current work. Report worktree, branch, exact SHA, tracked/untracked state,
> PR/pipeline state, reserved files, and the single next action. Explicitly
> relinquish ownership; do not delete or clean anything.

### Hand work to another agent

> The prior writer has relinquished this lane. Continue only from branch
> [branch] at exact pushed SHA [SHA]. Verify it against current Azure main and
> CURRENT_LANES. Do not adopt any other worktree or broaden the writable files.

### Release an accepted change

> Release only the accepted exact SHA for [package]. Confirm no other
> production/schema reservation, use the required Azure PR, wait for the
> automatic main run, verify exact live identity and affected routes, then
> close and clean up the lane. Do not manually queue a same-SHA fallback while
> an automatic run exists. If a manual fallback is genuinely required, enter
> that exact 40-character SHA in `manualProductionSourceVersion`; never combine
> it with a schema action.

## How to read status reports

Require these states separately:

- discussed;
- selected/activated;
- implementation branch;
- tests passed;
- independently reviewed, when required;
- owner accepted;
- PR policy passed;
- squash-merged;
- automatic main build passed;
- deployed;
- live verified;
- schema applied and verified, when applicable; and
- cleanup complete.

If a report only says “done,” ask which exact state it means.

## Things Pete should avoid

- Do not tell two agents to implement the same package or shared files.
- Do not use “go ahead” for several unrelated ideas at once; name the one next
  outcome and explicitly park the rest.
- Do not turn a discussion into runtime work merely because the mockup or idea
  is exciting.
- Do not queue a manual pipeline to make a slow or red Azure row disappear.
- Do not interpret a green PR as deployed or live.
- Do not delete old worktrees or branches until unique and untracked material
  is classified.
- Do not let a child branch continue across a parent's squash merge; rebuild it
  from current main.

## What the system and agents owe Pete

Pete should not have to remember hidden technical state. Before writing, the
agent must run the preflight and state the current package, branch, owner,
behind/ahead count, conflicting surfaces, and allowed next action. Before
release, the agent must identify the exact source SHA and active production
reservation. After release, the agent must close the branch/worktree and update
the live ledger so finished work does not remain operationally active.

The activation record is the one deliberate setup step from
`controlled_idle`, and it is also how another writer is added during
`active_delivery` when capacity remains. Its purpose is to make the selected
lane, branch, worktree, class, exclusive domains, and non-overlapping surfaces
visible to every other session before writing begins. It is not itself an
architecture round, feature review, or implementation package.

PeerSlate permits three active writers, but they are not interchangeable:

- At most two lanes may be `implementation` or `shared_foundation`.
- At most one lane may be `direction_authority`.
- At most one shared-foundation lane may be active.
- At most one active lane may be production-capable.
- A direction/authority lane may write only beneath `docs/initiatives/` or
  `artifacts/`; it cannot carry templates, styles, scripts, services, tests, or
  other runtime implementation.
- A path overlap or an exclusive-domain overlap is a stop even when a slot is
  numerically free. Typical domains include `product:profile`,
  `shared:global-shell`, `shared:auth`, `shared:data-schema`, and
  `shared:visual-foundation`.
- Both implementation lanes may prepare work, but production-boundary actions
  remain serialized through the existing merge/release authority.

An empty third slot is intentional when the proposed work depends on an active
lane or needs one of its domains. Read-only researchers and reviewers are not
writers and consume no lane.

Only an actually writing package belongs in `active_lanes`. A package waiting
for owner input, a visual-generation round, a dependency, or later resumption
must relinquish ownership with the controlled `--intent pause` transition.
The writer first commits and pushes the exact checkpoint. A separate
`work/YYYY-MM-DD-delivery-pause-<slug>` branch is then created from current
`origin/main`; it changes only `CURRENT_LANES.json` and
`CURRENT_BASELINE.yaml`, records the fetched work-branch commit, and is the only
branch merged for the pause. This prevents both failure modes: unfinished work
is neither merged merely to free capacity nor left only in an inaccessible
local checkout. A resume always requires fresh activation from current
`origin/main`, a new branch, and new path/domain collision checks.

Before merge or release, preflight compares the branch's actual changed paths
with its declared writable surfaces. A declared lane is therefore not
permission to let unrelated edits travel with the branch. A full class limit,
path collision, domain collision, or out-of-scope branch diff is a real stop.

The process is successful when Pete can keep having fun with the product while
the delivery system permits only a small, visible amount of work to become
production-intent at once.
