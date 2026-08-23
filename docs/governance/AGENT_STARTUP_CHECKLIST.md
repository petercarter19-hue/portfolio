# PeerSlate Agent Startup Checklist

Use this for a change, not a read-only discussion.

- [ ] Checked branch, status, Azure origin/main, and preserved unrelated work.
- [ ] Used a clean worktree when the existing checkout was dirty or owned.
- [ ] Read `CURRENT_BASELINE.yaml`, `CURRENT_LANES.json`, and the exact package
  claim; chose Routine, Bounded, or Protected.
- [ ] For implementation edits, passed `delivery_preflight.py --package
  <PACKAGE-ID> --intent write --fetch --require-clean` before editing.
- [ ] For a control-only transition, ran `--intent read` before editing, changed
  and committed only the exact claim, then ran the matching control intent with
  `--fetch --require-clean` before PR.
- [ ] Confirmed the branch, normalized mutable paths, and hierarchical domains
  do not collide with another active claim. No numeric capacity check applies.
- [ ] Confirmed the assignment: implementation normally continues through
  accepted merge unless explicitly `write_only`; reviewers remain claim-free;
  production authority is always withheld from repository claims.
- [ ] Read only the package and specialist contracts triggered by the work.
- [ ] Selected focused verification and one proportional completion record.
- [ ] Planned an immutable candidate, generic exact-SHA receipt, and fixed
  runtime-inert evidence file. Routine/Bounded use the writer's self-review
  receipt; Protected uses a read-only independent-review receipt.
- [ ] Kept deployment, schema, configuration, enablement, rollback, and live
  proof outside repository authority unless Pete separately authorizes the
  exact production operation.

For a new outcome, merge a one-claim activation before creating its worktree.
For a real authority expansion, transfer, pause, resume, or close, use its
one-claim control transition. Resume must preserve the fetched checkpoint and
rerun collisions. Keep the remote implementation branch through close.
Authority expansion applies only to a claim Pete explicitly narrowed to
`write_only` and requires a new opaque owner decision reference.
Stop on a genuine collision or trust-boundary problem, not an unrelated
historical gate.
