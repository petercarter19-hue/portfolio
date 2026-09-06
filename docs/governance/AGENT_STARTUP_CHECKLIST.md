# PeerSlate Agent Startup Checklist

Use this for a change, not a read-only discussion.

- [ ] Checked branch, status, Azure origin/main, and preserved unrelated work.
- [ ] Recorded the exact package, manager, role, task reference, and next
  authorized outcome. Selected the current role default from
  `AI_MODEL_AND_ROLE_ROUTING.md` and verified the effective model and effort
  in this task. Missing inspection is `unavailable`; a safe unfamiliar model
  label stays the observed label. Did not churn settings or warm caches.
- [ ] Ran the read-only lifecycle audit when locally initialized; reused the
  package's one registered durable worktree with `ensure` or exact `adopt`, and
  inspected `ensure.environment_readiness` for that exact worktree. Did not
  create an ad hoc checkout. Unavailable optional readiness does not change
  custody or grant authority. Unrelated grandfathered worktrees are not a
  global stop.
- [ ] Read `CURRENT_BASELINE.yaml`, `CURRENT_LANES.json`, and the exact package
  claim; chose Routine, Bounded, or Protected.
- [ ] For implementation edits, passed `delivery_preflight.py --package
  <PACKAGE-ID> --intent write --task-ref <WRITER-REF> --fetch --require-clean`
  before editing.
- [ ] For a control-only transition, ran `--intent read` before editing, changed
  and committed only the exact claim in the leased sparse `_control` singleton,
  then ran the matching control intent with the same `--task-ref` plus
  `--fetch --require-clean` before PR. An active-claim surface extension uses
  `--intent extend-surfaces` on a dedicated `delivery-extend-surfaces` branch;
  the assigned writer appends exact current-main tracked-file paths at the end
  of `surfaces` and changes nothing else.
- [ ] For owner reassignment, obtained Pete's exact opaque authorization,
  leased `_control` to the receiver on a dedicated owner-reassignment branch,
  confirmed the complete initialized registry has exactly one control record,
  no lock/pending ambiguity, and no malformed, duplicate, incompatible, or
  orphaned preparation state or inexact create/retire/control-repoint/
  branch-create journal custody, then ran
  `prepare-owner-reassignment` before editing the claim. Confirmed every active
  target/source durable record matched its exact pristine live Git path/task/
  branch/checkpoint, no exact or ancestor/descendant branch namespace collided,
  and the registry retained one completed tuple with the exact `[new branch]`
  response and source snapshot. Changed only `writer_ref`, `branch`, and the
  exact non-relinquishment handoff; passed local owner-reassignment preflight
  without CI/uninitialized bypass and with its terminal mutex-held registry,
  lease, pending, source, namespace, main, claims, old-branch, and successor
  reproof; and waited for the control PR to merge before the
  one-time consuming receiver `ensure` or write preflight. Confirmed receiver
  residue leaves proof and pending state unconsumed.
- [ ] Confirmed the branch, normalized mutable paths, and hierarchical domains
  do not collide with another active claim. No numeric capacity check applies.
- [ ] Confirmed the assignment: implementation normally continues through
  accepted merge unless explicitly `write_only`; reviewers remain claim-free;
  production authority is always withheld from repository claims.
- [ ] Read only the package and specialist contracts triggered by the work.
- [ ] Selected focused verification and one proportional completion record.
- [ ] Planned an immutable candidate, generic exact-SHA receipt, and fixed
  runtime-inert evidence file. Routine/Bounded use the writer's self-review
  receipt; Protected uses a read-only independent-review receipt. Review
  defaults to Azure/the pushed diff and creates no worktree; runnable isolation
  leases the one sparse singleton.
- [ ] Kept deployment, schema, configuration, enablement, rollback, and live
  proof outside repository authority unless Pete separately authorizes the
  exact production operation.
- [ ] Planned same-task `finalize-task` for temporary resources. After close,
  any durable retirement uses the exact registered path/task/HEAD and ordinary
  non-force Git removal only; a refusal preserves the worktree. Planned to
  carry the exact-session `usage_summary` into the completion record and to
  select each child session explicitly once.
- [ ] For a complete cross-platform transfer, verified the receiver's exact
  task, platform/account/project/repository access, effective role setting, and
  explicit acceptance. Transferred no credential or session-only authority.

For a new outcome, merge a one-claim activation before creating its worktree.
For a real authority expansion, transfer, owner reassignment, pause, resume, or
close, use its
one-claim control transition. Resume must preserve the fetched checkpoint and
rerun collisions. Keep the remote implementation branch through close.
Authority expansion applies only to a claim Pete explicitly narrowed to
`write_only` and requires a new opaque owner decision reference.
Stop on a genuine collision or trust-boundary problem, not an unrelated
historical gate.

Use compact event-driven updates for a decision, meaningful state change,
failure, completion, or required owner action. Do not add acknowledgement
loops, duplicate review, unrelated audits, cache warmers, or status-only
monitoring.
