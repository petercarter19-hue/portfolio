# PeerSlate - Start Here

## 1. Establish a safe base

```bash
git status --short --branch
git remote -v
git branch --show-current
git fetch origin --prune
git log -1 --format='%H %s' origin/main
```

- Azure DevOps `origin/main` is authoritative.
- Preserve dirty or unrelated work. Use a clean worktree instead of switching,
  resetting, cleaning, or adopting somebody else's checkout.
- Use a short-lived work branch from current `origin/main`; never push to main.
- After the lifecycle bootstrap, never create an ad hoc worktree. Run the
  read-only `python scripts/worktree_lifecycle.py audit --json`, then reuse the
  active package's registered durable worktree with `ensure`, or use exact
  bookkeeping-only `adopt` when its branch already has a worktree. Unrelated
  grandfathered worktrees are observations, not a global stop. On a new
  machine, initialize once through
  `docs/governance/WORKTREE_LIFECYCLE.md`; do not improvise another checkout.

## 2. Read only what the task needs

Read `docs/governance/CURRENT_BASELINE.yaml`, the small
`docs/governance/CURRENT_LANES.json` index, and the package's JSON claim under
`docs/governance/lane_claims/`. Before implementation edits, run:

```bash
python scripts/delivery_preflight.py --package <PACKAGE-ID> --intent write --task-ref <WRITER-REF> --fetch --require-clean
```

Use `--intent read` for read-only work; failures stop. A control-only
activation, authorize, surface extension, transfer, pause, resume, or close
uses `read` before the edit, changes and commits only the exact claim on its
dedicated control branch, then runs the matching control intent with `--fetch
--require-clean` before PR. It may not change an implementation surface.

| Path | Use for | Additional authority |
|---|---|---|
| Routine | Copy, isolated correction, focused test, internal refactor, documentation | Code and focused verification. |
| Bounded | Approved feature or route inside an established package and architecture | Package and directly affected contract. |
| Protected | Identity, authorization, privacy, canonical data, migration, deletion/publication, consequential AI, shared infrastructure, or materially revised visual direction | Package, named specialist standard, risk evidence, and independent review. |

## 3. Activate only a selected outcome

Pete first names the exact outcome. From current main, lease the permanent
sparse control singleton for a clean
`work/YYYY-MM-DD-delivery-activation-<slug>` branch, then add exactly one
`docs/governance/lane_claims/<PACKAGE-ID>.json` file:

```bash
python scripts/worktree_lifecycle.py control --package <PACKAGE-ID> --task-ref <WRITER-REF> --branch work/YYYY-MM-DD-delivery-activation-<slug> --base origin/main --execute
```

Record:

- package, outcome, opaque writer task reference, and future work branch;
- Routine, Bounded, or Protected path;
- repository authority (`through_merge` by default or explicit `write_only`);
- normalized mutable surfaces and hierarchical domains;
- the package-reserved claim, receipt, and runtime-inert evidence paths, plus
  review requirement;
- `production_authority: withheld`, exact current main SHA, and owner outcome
  reference.

Commit the one-file activation and run:

```bash
python scripts/delivery_preflight.py --package <PACKAGE-ID> --intent activate --task-ref <WRITER-REF> --fetch --require-clean
```

Merge the control PR, then run `worktree_lifecycle.py ensure --package
<PACKAGE-ID> --task-ref <WRITER-REF> --execute` to create or return the one
durable implementation worktree. There is no numeric writer, class, or
production-capable-lane cap. Disjoint writers may all proceed. Duplicate
branches, overlapping claimed paths, and hierarchical domain collisions fail
closed. Reviewers consume no writer claim and default to Azure or the pushed
diff; runnable isolation uses the one leased sparse singleton.

## 4. Work through merge

Implementation normally continues through accepted merge. Every merge uses one
proof path:

1. Commit and push an immutable candidate SHA.
2. Routine/Bounded: complete self-review and issue a `self` receipt using the
   writer reference. Protected: obtain a read-only independent review and
   `independent` pass receipt. Correct findings and freeze again as needed.
3. Add only `lane_claims/receipts/<PACKAGE-ID>.json` and runtime-inert
   `lane_claims/evidence/<PACKAGE-ID>.md`, push, then run:

```bash
python scripts/delivery_preflight.py --package <PACKAGE-ID> --intent merge --candidate-sha <REVIEWED-SHA> --task-ref <WRITER-REF> --fetch --require-clean
```

This admits disjoint main movement and blocks candidate tampering, collisions,
missing review, and non-evidence edits after review. Normal claims need no
separate grant.

A claim explicitly narrowed to `write_only` may write but cannot merge. If Pete
expands it, a `delivery-authorize` branch changes only `repository_authority`
to `through_merge` and `owner_outcome_ref` to the new opaque decision reference:

```bash
python scripts/delivery_preflight.py --package <PACKAGE-ID> --intent authorize --fetch --require-clean
```

Merge that control PR before implementation merge.

## 5. Change claim state only when needed

- Extend surfaces: when an active package discovers one or more exact files it
  must also change, its assigned writer leases `_control` from current main on
  `work/YYYY-MM-DD-delivery-extend-surfaces-<slug>`, appends only those
  normalized paths already proved as tracked file blobs on current main to the
  end of `surfaces`, and commits only that claim. The same task reference must
  equal the claim's `writer_ref`:

  ```bash
  python scripts/delivery_preflight.py --package <PACKAGE-ID> --intent extend-surfaces --task-ref <WRITER-REF> --fetch --require-clean
  ```

  The transition refuses a stale or dirty control checkout, another task or
  package, an inactive claim, a non-dedicated branch, malformed, duplicate, or
  unproved or directory-like additions, any removal/replacement/reorder or
  other field/file change, same-claim overlap, and exact/parent/child collisions
  in the full current claim set.
- Transfer: push the exact checkpoint, record opaque from/to task references
  and explicit relinquishment in the claim, then validate on a dedicated
  `delivery-transfer` control branch with `--intent transfer`.
- Pause: push the exact work branch, set the claim to `paused` with that fetched
  checkpoint on a `delivery-pause` branch, then run `--intent pause`. Do not
  merge unfinished implementation merely to release ownership.
- Resume: on a `delivery-resume` branch, change only `state` from `paused` to
  `active`, then run `--intent resume`. The fetched branch must still equal the
  preserved checkpoint, and current branch/path/domain collisions rerun.
- Close: after the accepted repository SHA is on main, set the claim to
  `closed` with `merged_sha` and UTC `closed_at` on a `delivery-close` branch,
  then run `--intent close`. The check proves the reviewed candidate paths and
  bytes were introduced by that recorded main commit. Keep the remote
  implementation branch through close; if it was deleted, re-push the exact
  reviewed branch before retrying.
- Evidence errata: the only way to amend a CLOSED package's one fixed
  `lane_claims/evidence` file. With Pete's authorization, lease the `_control`
  singleton for that closed package, branch
  `work/YYYY-MM-DD-delivery-evidence-errata-<slug>` from current main, and
  commit exactly that one file, containing
  `<!-- evidence-errata-authorization: <owner-ref> -->` for the supplied
  reference. Change no claim. Validate with
  `--intent evidence-errata --owner-authorization-ref <owner-ref>`; it fails
  closed on any other path, any claim delta, a non-closed claim, a reused
  marker, or a stale branch, and it admits only that evidence-only PR —
  never a deployment or a claim change.

Every control transition above first leases `_control` with
`worktree_lifecycle.py control --package <PACKAGE-ID> --task-ref <TASK-REF>
--branch <CONTROL-BRANCH> --base origin/main --execute`, passes that same
`--task-ref` to delivery preflight, and releases the clean lease with
`worktree_lifecycle.py finalize-task --task-ref <TASK-REF> --execute` in the
same task.

## 6. Keep deployment separate

PR and automatic main runs build and test only. A production web deployment is
allowed only in a manually queued main run with all three values:

- `forceProductionDeploy=true`;
- `manualProductionSourceVersion=<exact 40-character main SHA>`;
- `productionAuthorizationReference=<Pete's explicit decision reference>`.

Schema operations remain manual, separately gated, and cannot share a web
deployment run. Merge, deployment, schema, enablement, rollback, and live
verification are separate truthful states.

## 7. Finish proportionately

Use `docs/templates/OWNER_TECHNICAL_COMPLETION_REPORT.md` once. Record outcome,
base/final SHA, changed paths, tests, review, PR/merge state, deployment state,
honest limits, and next action. Stop for a real ownership, privacy,
authorization, migration, deletion, or material-visual conflict - not an
unrelated historical record.

After claim close, retire a package worktree only through the exact registered
path, task, and expected HEAD. The guard requires a closed fetched claim,
pristine tracked/untracked/ignored state, an exact server-confirmed claimed-
branch tip (never a stale local ref or local-only tag), and ordinary non-force
Git removal. Otherwise it preserves the worktree and states the blocker.
