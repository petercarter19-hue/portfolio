# PeerSlate Agent Startup Checklist

Use this for a change, not for a read-only discussion.

- [ ] Checked branch, status, remote, and current `origin/main`; preserved work
  not owned by this task.
- [ ] Used a clean task branch/worktree when the existing checkout is not safe
  to touch.
- [ ] Read `CURRENT_BASELINE.yaml` and classified the work as Routine, Bounded,
  or Protected under `START_HERE.md`.
- [ ] Read `CURRENT_LANES.json` and passed `scripts/delivery_preflight.py` for
  the exact package and intended read/write/release action.
- [ ] For a new lane, confirmed Pete selected one exact outcome and used the
  ledger-only activation flow before implementation. Activation may start
  from `controlled_idle`, or from `active_delivery` only when the three-lane
  class limit has capacity and neither mutable paths nor exclusive domains
  conflict. At most two implementation/shared-foundation lanes and one
  direction/authority lane may be active. The direction lane is restricted to
  initiative documentation/evidence, and only one lane may be production-capable.
- [ ] Confirmed this package is actually writing. Read-only research and a
  preserved pause consume no writer lane; resumption requires fresh activation.
- [ ] For a pause, committed and pushed the intended checkpoint, then used a
  separate control-only pause branch from current `origin/main`; did not merge
  the unfinished package merely to update capacity.
- [ ] Read the package and specialist contract only when the selected path
  requires them.
- [ ] Confirmed the writer and editable files/domain; a manager handoff is
  required only when work actually changes hands or crosses an owned lane.
- [ ] For an in-place writer change, confirmed the prior writer pushed and
  relinquished the exact SHA, used a dedicated control-only transfer branch,
  changed only the permitted lane transfer fields, and passed `--intent
  transfer --fetch --require-clean` before the receiver wrote.
- [ ] For a completed non-production direction/authority lane, used the
  separate grant -> merge -> close controls: exact pushed/reviewed SHA,
  pre-existing Pete merge decision, review evidence at that SHA,
  non-overlapping behind-main proof, exact main tree equivalence, and removal
  of all mutation authority at close.
- [ ] If that candidate predates current control code, left it untouched and
  ran merge preflight from a separate clean current-main verifier with its
  absolute registered `--candidate-worktree` path; did not rebase, overlay,
  detach, or run the candidate's older validator; retained its remote branch
  through close with PR source-branch deletion disabled.
- [ ] For Protected work, named the specific privacy, security, data, release,
  or material-visual evidence required before release.
- [ ] Chosen focused verification and the proportional completion record.

Stop when a real ownership, privacy, authorization, migration, or visual
authority conflict cannot be resolved. Do not create a stop condition from
unrelated documentation or a closed/historical package.
