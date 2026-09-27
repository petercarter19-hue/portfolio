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

Use `--intent read` for read-only work; failures stop. Existing active
cross-claim path or hierarchical-domain collisions are the narrow exception:
`read` reports them as explicit warnings/facts and may pass because it grants
no repository authority. Malformed claims, branch collisions, and every other
claim-set defect remain fatal. Every mutating intent still fails when its
candidate claim set contains any path/domain collision; a pre-transition
authority collision becomes nonfatal only when the exact complete candidate
claim set removes it and all ordinary intent-specific gates also pass. A
control-only activation, authorize, surface extension, transfer, owner
reassignment, pause, resume, or close
uses `read` before the edit, changes and commits only the exact claim on its
dedicated control branch, then runs the matching control intent with `--fetch
--require-clean` before PR. It may not change an implementation surface.

Codex lifecycle and mutating preflight calls resolve the actual
`CODEX_THREAD_ID` automatically as `session:<UUID>`; they never use inherited
`CODEX_SESSION_ID`. Legacy `PEERSLATE_CALLER_REF` remains compatible, but it
must agree with native identity. For a Pete-operated handoff to an external
runtime, the current control-lease holder registers a scoped caller context as
documented in `docs/governance/WORKTREE_LIFECYCLE.md` and supplies its opaque ID
in the handoff. The receiver passes `--caller-context <ID>`; Pete does not set a
user or global environment variable. A context identifies the caller only and
does not grant a claim, lease, custody, repository, or production authority.

| Path | Use for | Additional authority |
|---|---|---|
| Routine | Copy, isolated correction, focused test, internal refactor, documentation | Code and focused verification. |
| Bounded | Approved feature or route inside an established package and architecture | Package and directly affected contract. |
| Protected | Identity, authorization, privacy, canonical data, migration, deletion/publication, consequential AI, shared infrastructure, or materially revised visual direction | Package, named specialist standard, risk evidence, and independent review. |

## 3. Activate only a selected outcome

### Required-check repair when claim-only CI cannot pass

This is a durable, narrowly scoped alternative for a required security or
delivery-check repair. It changes the existing local admission predicates,
not Azure policies or the requirement for real CI. Ordinary activation stays
claim-only. Product/pipeline changes, unrelated claims and unreviewed bytes
cannot use this path. Ownership collisions still stop it.

1. Obtain Pete's exact selected outcome and the actual writer's accepted
   control custody. Use `control-custody` recovery in
   `docs/governance/WORKTREE_LIFECYCLE.md` if the old chat is lost; require
   external quiescence and the receiver's own acceptance. Do not spoof the
   original task or treat a launched process as acceptance.
2. Prepare the full candidate outside the checkout before implementation
   writes. Create a fresh Protected claim plus only the supported gate-repair
   files. `REPAIR_SURFACES` in `scripts/delivery_preflight.py` is the fixed
   boundary; changing that boundary itself requires exact independent review.
   Reserve exactly those files plus the claim's fixed receipt/evidence paths.
3. Prepare an external JSON manifest with exactly `authorization`,
   `precommit_review`, and `merge_review`. Authorization contains
   `schema_version: 1`, `package`, actual `writer_ref`,
   `owner_authorization_ref`, `failure_evidence_ref`, exact `base_sha`,
   dedicated activation `branch`, and `files` mapping repository-relative
   regular-file paths to exact Git blob IDs (including the claim). Owner and
   failure references must identify real reviewable decisions/evidence.
4. Independent precommit review records `reviewer_ref`, `review_ref`,
   `result: pass`, and `authorization_sha256`: SHA-256 of UTF-8 JSON for the
   authorization with sorted keys, separators `(',', ':')`, and
   `ensure_ascii=False`. Keep `merge_review: null` at activation. Opaque
   references attest external decisions; this tool does not authenticate them.
5. After that review and the owner's explicit authorization, materialize and
   commit those exact files from the actual leased control task using guarded
   writes. Run `--intent repair-activate --repair-manifest <absolute-path>
   --owner-authorization-ref <owner-ref> --lease-token <current-token>
   --task-ref <actual-writer> --package <package> --fetch --require-clean`.
   The optional `--repo <checkout>` selects the validated repository explicitly;
   every ordinary identity/collision/base check still applies.
6. Obtain independent review of the exact commit. Store the ordinary review
   receipt schema in the external manifest's `merge_review`, naming that SHA.
   Run the same preflight with `--intent repair-merge --candidate-sha <SHA>`.
   HEAD must equal the reviewed commit; no unreviewed tail is admitted.
7. Open a normal Azure PR and require every existing server policy, full scan
   and CI check against the actual source/target. Local repair admission does
   **not** attest that CI passed. Do not use skip-CI, policy waivers, forced
   merge or direct-main pushes. Preserve the independent review and owner
   manifest in the package evidence after merge through its ordinary durable
   worktree, then continue normal lifecycle operations. This admission grants
   no deployment authority.

Before these mechanisms have reached accepted main, executing an external
reviewed copy is a one-use bootstrap exception requiring Pete's explicit
hash-bound approval. The code cannot grant its own acceptance. Keep the
bootstrap separate from the durable rules and preserve all current claim
collisions; stage scanner-only admission before lifecycle changes if needed.

### Ordinary activation

Pete first names the exact outcome. From current main, lease the permanent
sparse control singleton for a clean
`work/YYYY-MM-DD-delivery-activation-<slug>` branch, then add exactly one
`docs/governance/lane_claims/<PACKAGE-ID>.json` file:

The unrevoked standing bounded Workshop completion decision in
`docs/governance/DECISIONS.md` also satisfies this selection gate for only a
concrete minimum repository follow-up needed to complete the already accepted
Workshop use-disclosure outcome while its parent claim is active or paused.
Each child claim must cite the exact standing reference and failed gate. The
decision expires at parent close or Pete's revocation and grants none of the
separately gated production, schema, destructive, identity/privacy-policy,
credential, spending, external-operation, or material-visual authorities.

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
durable implementation worktree. Its `environment_readiness` field is the
automatic read-only startup observation for that exact worktree. Assess
`fail` or `unavailable` against the requested operation; only the existing
preflight and custody rules gate work. The observation never rolls back
successful custody or proves authority.
There is no numeric writer, class, or
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
- Release surfaces: this dormant Protected operation is available only after
  accepted `CURRENT_LANES.json` schema 4 and machine-local registry schema 2.
  Candidate A does not perform that cutover. At a later authorized boundary,
  qualify every active durable writer as quiescent and use
  `migrate-registry-v2` once; it binds the actual caller to `--task-ref`, refuses
  candidate delivery-tool bytes and pending state, creates an exact-byte
  schema-1 backup, preserves every custody record, seals the schema-2 digest,
  and atomically validates the one live registry. Recovery refuses if that
  deterministic backup is missing or changed. The separately reviewed index
  cutover then enables the
  capability.

  The active writer leases `_control` on
  `work/YYYY-MM-DD-delivery-release-surfaces-<slug>` and, from its pristine
  durable worktree at exact local/remote checkpoint C, runs `scope-release
  prepare` with a proposal containing only retained surfaces/domains, retained
  responsibility-to-domain mappings, rationale, and an
  `accepted_introductions` list (normally empty), plus the writer's explicit
  `quiescence_ref`. The tool records exact
  C/M mode/blob or absence for every released path. A path with net branch
  delta requires an accepted-main commit and exact-candidate receipt in that
  list; unchanged paths must not assert one. The returned proof is the
  sole optional `scope_release` object in the claim. Commit only that claim and
  validate with:

  ```bash
  python scripts/delivery_preflight.py --package <PACKAGE-ID> --intent release-surfaces --task-ref <WRITER-REF> --fetch --require-clean
  ```

  The registry freeze remains while CI runs even if `_control` is released.
  Complete it only after the exact reduced claim is accepted through the
  recorded prepared-main-to-current-main transition lineage; cancel it
  only while the exact prior claim and C remain authoritative and no server
  outcome is uncertain. An accepted reduction becomes `scope_sync_required`.
  Ordinary writes stay blocked until `reconcile-main` imports current main.
  Released paths are not implicitly reacquired; use ordinary exact-file
  extension after fresh admission if later work genuinely needs them.
- Transfer: push the exact checkpoint, record opaque from/to task references
  and explicit relinquishment in the claim, then validate on a dedicated
  `delivery-transfer` control branch with `--intent transfer`.
- Owner reassignment: use only when Pete explicitly replaces a writer without
  voluntary relinquishment. Lease `_control` for the receiving task on a
  current-main `work/YYYY-MM-DD-delivery-owner-reassignment-<slug>` branch.
  Before editing the claim, prepare one distinct, normalized, unclaimed and
  server-absent successor branch at the exact fetched old-branch checkpoint:

  ```bash
  python scripts/worktree_lifecycle.py prepare-owner-reassignment --package <PACKAGE-ID> --task-ref <RECEIVER-REF> --successor-branch <NEW-WORK-BRANCH> --expected-checkpoint <OLD-REMOTE-SHA> --owner-authorization-ref <OWNER-REF> --execute
  ```

  When the vanished writer advanced the pristine registered checkout and its
  server branch but the machine-local durable record still names an older
  HEAD, first obtain a bounded orchestrator/lifecycle reference proving that
  source task is unavailable and add
  `--source-unavailable-ref <EVIDENCE-REF>`. The tool accepts this recovery only
  when the old recorded HEAD is an ancestor and the exact claim, old task,
  branch, canonical path, pristine live HEAD, local branch, and fetched server
  tip all agree. It journals the registry correction with successor creation,
  rolls the correction back when the successor remains absent, and preserves
  the proof in the completed preparation's digest-bound immutable tuple. The
  proof-bearing record and its pending or completed/consuming/consumed state
  must remain bidirectionally linked; a missing or orphan link refuses before
  recovery. Any ambiguous state remains for investigation. The receiver never impersonates the
  old writer. A `superseded` claim is terminal, not live ownership.

  This command requires a complete initialized registry, exactly one total
  `control_singleton` record, and that exact active leased control singleton
  with no registry lock or unresolved pending operation. It schema-validates
  every completed/consuming/consumed preparation and rejects malformed,
  duplicate, type-confused, orphan, or incompatible state, including a pending
  worktree record without its exact create journal and any create, retire,
  closed-custody-retire, control-repoint, or branch-create journal without its
  exact record linkage,
  before remote mutation. Before
  journaling or pushing, it reconciles every active target-package/source-branch
  durable record against one exact absolute live Git path, old task, old
  branch, checkpoint HEAD, and pristine state, and rejects duplicates. It also rejects
  exact and ancestor/descendant namespace collisions across local heads,
  origin-tracking refs, live claims, worktrees, and active registry custody.
  The guarded absent-ref create never force-moves a ref and immediately proves
  both remote branches still equal the checkpoint, then rechecks current main
  and the strict live-claim snapshot. Normal and crash recovery use the same
  final server reproof immediately before completing the preparation. It
  creates no local branch, changes no
  old branch or worktree, and refuses dirty/unpushed old-writer state,
  collisions, races, or ambiguous push recovery.

  Successful preparation persists one completed tuple binding the package,
  owner reference, old/new refs and branches, checkpoint, control branch,
  prepared main, Git's exact `[new branch]` response, and the source snapshot.
  Then change only the claim's `writer_ref`, `branch`, and `handoff`. The exact handoff is
  `type: owner_reassignment`, opaque `from_ref`/`to_ref`, old/new branch names,
  `checkpoint_sha`, and `owner_authorization_ref`; never assert
  `relinquished`. Commit and run:

  ```bash
  python scripts/delivery_preflight.py --package <PACKAGE-ID> --intent owner-reassignment --task-ref <RECEIVER-REF> --owner-authorization-ref <OWNER-REF> --fetch --require-clean
  ```

  This intent is the local-registry exception to ordinary CI/uninitialized
  tolerance: it requires the same exclusively leased `_control`, no lock or
  pending ambiguity, and one unconsumed completed tuple whose digest and live
  source snapshot still match, while rechecking that the successor namespace
  remains collision-free. A terminal mutex-held registry/lease/pending
  validation closes admission after all owner-specific proofs and repeats the
  source, namespace, main, claims, old-branch, and successor checks while the
  mutex remains held. Missing, mismatched, mutated,
  duplicated, or consumed proof fails closed. Merge that one-claim PR before
  the receiver runs `ensure` or any write preflight. Post-merge `ensure`
  atomically consumes the tuple once, preserves a registered old-writer
  checkout as a non-writable reassignment source, and creates a distinct
  successor durable worktree. A
  dirty or residue-bearing receiver remains pending with its proof unconsumed.
  Replayed consumed proof is refused; the successor may advance normally after
  its first ensure. A later legitimate reassignment preserves older sources and
  history under their own handoffs while consuming only the current source.
  Recovery never deletes or force-moves the old branch or worktree.
- Retire unavailable-writer closed custody: use only the separately claimed
  Protected cleanup package and run from that package's exact active durable
  worktree after its reviewed mechanism is merged. Supply Pete's current exact
  cleanup authorization reference and a fresh truthful source-unavailability
  reference dedicated to one target:

  ```bash
  python scripts/worktree_lifecycle.py retire-closed-custody --cleanup-package <CLEANUP-PACKAGE> --task-ref <CLEANUP-WRITER-REF> --target-package <CLOSED-PACKAGE> --path <EXACT-CANONICAL-WORKTREE-PATH> --branch <ORIGINAL-BRANCH> --source-task-ref <ORIGINAL-WRITER-REF> --expected-head <EXACT-SERVER-SHA> --owner-authorization-ref <OWNER-REF> --source-unavailable-ref <TARGET-SPECIFIC-EVIDENCE-REF> --execute
  ```

  This is not ordinary writer retirement and does not transfer source
  authority. The command is unavailable until fetched main contains the
  accepted independent receipt and evidence, all reviewed lifecycle surfaces
  match the reviewed candidate on both main and the cleanup branch, and the
  executing lifecycle script is that exact main blob. The tool also requires
  the cleanup claim's exact Protected policy and
  surfaces, its current writer/worktree/branch/server tip, and the target's
  fetched closed claim, original task, canonical active durable registry
  record, pristine live checkout, local branch, and exact server tip. Only a
  registry HEAD equal to or ancestral to the expected HEAD may be reconciled.
  A lease, lock, unrelated pending journal, duplicate, nesting, reparse point,
  path ambiguity, residue (including ignored files), missing ref,
  behind-server state, divergence, or any race is a refusal. A distinct
  before/after journal makes process-death recovery preserve or finish only the
  proven target. If the target is still present, recovery re-proves its exact
  repository, canonical/reparse-safe path, branch, live/local HEAD, nesting,
  and pristine state before clearing the journal as preserved; a mismatch
  retains the journal. The retired record keeps the original `task_ref` and
  stores the cleanup caller and both evidence references in separate custody
  proof.
  Ordinary non-force `git worktree remove` is the only removal; branches, tags,
  and refs are never deleted.
- Retire an allowlisted historical checkout: use `retire-historical` only from
  the exact active durable worktree of its Protected cleanup package after the
  mechanism, allowlist, claim, evidence, and independent-pass receipt have
  merged. Supply one exact allowlisted path/branch/HEAD tuple and Pete's owner
  authorization reference:

  ```bash
  python scripts/worktree_lifecycle.py retire-historical --cleanup-package <CLEANUP-PACKAGE> --task-ref <CLEANUP-WRITER-REF> --path <EXACT-CANONICAL-PATH> --branch <EXACT-BRANCH> --expected-head <EXACT-SERVER-SHA> --owner-authorization-ref <OWNER-REF> --execute
  ```

  Admission requires the claim and evidence bytes, allowlist, and every shared
  lifecycle surface to match at the reviewed candidate, fetched main, and the
  cleanup branch, while the accepted receipt must match on main and the cleanup
  branch. The target must still be exactly the clean, registered
  grandfathered observation reviewed in the allowlist, with matching live,
  local-ref, and server-ref custody. Active, paused, or superseded claims;
  duplicate live path or branch custody; detached or nested worktrees; primary, managed, synthetic,
  reassignment, protected, or reparse paths; and tracked, untracked, or ignored
  residue all refuse. A crash journal can reconcile only the same request.
  Removal uses ordinary non-force `git worktree remove`; it never deletes refs,
  prunes, collects garbage, rewrites history, resets, cleans, or recursively
  deletes a path.
- Pause: push the exact work branch, set the claim to `paused` with that fetched
  checkpoint on a `delivery-pause` branch, then run `--intent pause`. Do not
  merge unfinished implementation merely to release ownership.
- Resume: on a `delivery-resume` branch, change only `state` from `paused` to
  `active`, then run `--intent resume`. The fetched branch must still equal the
  preserved checkpoint, and current branch/path/domain collisions rerun.
- Reconcile main: after ordinary resume or accepted scope release, an active
  writer whose owned paths intersect newer main uses lifecycle
  `reconcile-main start`. The operation pins source C and target M in the
  registry before a normal non-rewriting merge, imports unowned paths exactly
  from M, and retains only the package's exact unchanged C review receipt and
  evidence when main has not changed them. It exposes only owned conflicts for
  resolution and digests every other initial index entry so resolution cannot
  edit an owned non-conflicted path,
  and records
  `prepared`, `merging`, `resolved`, `committed`, `pushed`, then `completed` or
  `refresh_required`. Continue only the exact operation ID. Never reset,
  force-push, select ours for an unowned conflict, or replay an uncertain push.
  A committed R is preserved even when main advances; `refresh_required`
  blocks ordinary work until a fresh R-to-current-main reconciliation. The
  resulting combined candidate requires its own affected tests, exact-SHA
  review, and current-target CI.
- Supersede: the terminal disposition for an activated-but-unmerged package
  that was rejected and replaced or withdrawn. It is distinct from close:
  nothing was delivered. From a `paused` claim whose pushed checkpoint is
  preserved, and only with Pete's explicit authorization reference, change
  only the claim on a dedicated
  `work/YYYY-MM-DD-delivery-supersede-<slug>` branch: set `state` to
  `superseded`, add UTC `superseded_at`, and add a `supersession` record
  holding `owner_authorization_ref` plus exact closed replacement package
  references in `superseded_by` or an exact `withdrawal_reason`. Then run
  `--intent supersede --owner-authorization-ref <owner-ref>`. The transition
  refuses any package with an accepted review receipt on origin/main, any
  merged or delivered history, a moved or missing checkpoint branch, or a
  checkpoint already reachable from origin/main. Superseded is terminal:
  no resume, close, pause, transfer, or write, and the claim branch name
  stays reserved because the unmerged bytes exist only there.
- Close: after the accepted repository SHA is on main, set the claim to
  `closed` with `merged_sha` and UTC `closed_at` on a `delivery-close` branch,
  then run `--intent close`. The check proves the reviewed candidate paths and
  bytes were introduced by that recorded main commit. Operations-only
  closed-custody cleanup may instead use the independently reviewed immutable
  completion evidence and originating-registry proof specified in
  `docs/governance/WORKTREE_LIFECYCLE.md`; arbitrary empty candidates still fail.
  Keep the remote
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

For a writable package, record the focused pre-change command and explicit
criterion IDs in its single fixed `lane_claims/evidence/<PACKAGE-ID>.md`
`package-acceptance-json` block, then commit that plan before implementation.
The criterion text and baseline stay unchanged through the reviewed candidate.
Use this JSON shape inside the named fenced block (one block per package):

```package-acceptance-json
{
  "schema_version": 1, "package": "<PACKAGE-ID>", "plan_sha": null,
  "baseline": [{"command": "<focused command>", "exit_code": 0,
                "observation": "<actual pre-change result>"}],
  "criteria": [{"id": "behavior", "expected": "<specific outcome>",
                "verification": "<how it will be observed>"}],
  "candidate_sha": null, "checks": []
}
```

After committing the plan, fill `plan_sha` with that commit's SHA in the
implementation candidate. A failed initial baseline may stay as history when
a later pre-change entry for the same command proves it resolved. If its latest
result is still red, a passing automated candidate check must name that exact
command in `resolves_baseline_command`. Do not rewrite the predefined baseline
or criteria.
After exact-SHA review, add each criterion's observed result, exact source,
and candidate SHA to `checks` as
`{ "criterion_id": "behavior", "result": "pass", "kind": "automated", "candidate_sha": "<REVIEWED-SHA>", "source_ref": "<exact output/source>", "observed": "<semantic result>" }`.
For manual/browser checks, add `provenance` with `observer_ref`,
`captured_at`, and the same exact `source_ref`. A passing process exit
alone does not establish the criterion's meaning. Commit only the allowed
receipt/evidence tail and run:

```bash
python -B scripts/package_acceptance.py check --package <PACKAGE-ID> --candidate <REVIEWED-SHA>
```

An absent, failed, blocked, unmapped, or stale proof makes this agent-executed
completion check incomplete. Read-only work can explicitly report
`python -B scripts/package_acceptance.py check --package <PACKAGE-ID> --read-only`
as skipped. This helper does not grant a claim, replace
`delivery_preflight.py`, or enforce OS permissions.

Use `docs/templates/OWNER_TECHNICAL_COMPLETION_REPORT.md` once. Record outcome,
base/final SHA, changed paths, tests, review, PR/merge state, deployment state,
honest limits, next action, and the non-gating `usage_summary` returned by
`worktree_lifecycle.py finalize-task`. An exact `session:<UUID>` task ref
selects the root session automatically; repeat `--usage-session-id <UUID>`
only for explicitly selected child sessions. Do not infer missing waiting,
outcome, rework, intervention, model, or cost evidence from token counters.
Stop for a real ownership, privacy,
authorization, migration, deletion, or material-visual conflict - not an
unrelated historical record.

After claim close, retire a package worktree only through the exact registered
path, task, and expected HEAD. The same original registered task may also retire
after terminal supersession when the fetched claim names at least one exact
replacement package and every named replacement claim is closed on fetched
main. The guard requires the claim and registry branch to match, pristine
tracked/untracked/ignored state, exact live/local/server HEAD custody, and
ancestor-safe reconciliation of an older registry HEAD. Removal remains
ordinary non-force Git removal; supersession never grants a cleanup writer or
replacement writer the original task's custody. Otherwise the tool preserves
the worktree and states the blocker.
