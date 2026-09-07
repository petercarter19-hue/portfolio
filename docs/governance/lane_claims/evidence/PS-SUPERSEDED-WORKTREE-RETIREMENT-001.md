# PS-SUPERSEDED-WORKTREE-RETIREMENT-001 candidate evidence

## Authority and boundary

- Owner outcome: `session:01a07158-684b-74a2-a47e-7ca0e91889b7/owner-finish-2026-09-07`.
- Writer: `agent:/root/historical_writer`.
- Delivery: Protected, repository authority through accepted merge, production
  withheld, independent review required.
- The change extends ordinary durable-worktree retirement only for the exact
  original registered task after a terminal supersession with closed named
  replacements. It grants no cleanup-writer or replacement-writer override.
- Branches, refs, tags, stashes, history, unrelated work, production,
  deployment, schema, identity, product, and visual state remain outside scope.

## Candidate behavior

- Retains the existing closed-claim retirement path and admits a fetched
  `superseded` claim only when `superseded_by` is a nonempty, valid, unique
  package list and every named replacement claim is closed on fetched main.
- Requires the caller to equal the target worktree's exact registered
  `task_ref`; the supersession and replacement identities cannot authorize the
  removal.
- Requires matching claim/registry branch, live worktree HEAD, local branch
  ref, server branch tip, and requested expected HEAD.
- Reconciles an older registry HEAD only when the recorded commit is available
  and an ancestor of the exact live/local/server expected HEAD.
- Preserves the existing pristine tracked/untracked/ignored state, exact
  managed path, repository, reparse, nesting, pending-operation, mutex,
  current-working-directory, and ordinary non-force Git removal guards.

## Validation and review

- Fresh write preflight passed from accepted activation main
  `1fb88c175d7087273029c7b8cc4319f4f110d379`.
- Focused superseded/ordinary retirement tests passed 4/4 in 29.998 seconds.
  They cover exact original custody, closed-replacement admission, open
  replacement refusal, wrong-task refusal, residue refusal, ancestor-safe stale
  registry reconciliation, nonancestor refusal, and existing ordinary
  retirement protections.
- The final full lifecycle suite passed 100/100 in 1093.516 seconds with
  `python -B -m unittest tests.test_worktree_lifecycle`.
- Syntax parsing and `git diff --check` passed. Strict status contained only the
  four claimed implementation/docs/test paths before the candidate commit and
  was clean after push.
- Self-review corrected an intermediate ephemeral-retirement regression and
  added explicit local-ref proof before stale registry reconciliation. Both
  corrections are included in the tested candidate.
- Independent reviewer `agent:/root/historical_review` passed exact candidate
  `774992de20149d44b5a8d445ed6ae9e5d4e9f850` at
  `2026-09-07T22:49:42Z`, after verifying the remote branch tip was exact, with
  no findings.

## Preserved target

No package 001 worktree mutation occurred before review or merge. Its path,
branch, local/server checkpoint `cd17e72a2e8e65c2a234439e6bfbc71943d99721`,
and untracked `GROK_STATUS.md` remain preserved. The file's supported external
copy is recorded separately under evidence allocation
`e3c45973f8ec3a42c0eca564` with SHA-256
`AA31F48A5E67E3E572EB1F984D9E29AB9327A1D59527D32AC06F44A7725E5572`.

<!-- evidence-errata-authorization: session:01a07158-684b-74a2-a47e-7ca0e91889b7/owner-finish-2026-09-07 -->

## Accepted operational completion

- The independently reviewed mechanism candidate `774992de20149d44b5a8d445ed6ae9e5d4e9f850` was accepted by implementation PR 962 after required build 2645. Its mechanism bytes reached main at `9cf83d82f306a60486ca62764b5595bca76c2c2d`.
- Before source removal, the only old package residue, `GROK_STATUS.md`, was preserved at evidence allocation `e3c45973f8ec3a42c0eca564`. The copy is 3,207 bytes with SHA-256 `AA31F48A5E67E3E572EB1F984D9E29AB9327A1D59527D32AC06F44A7725E5572`.
- The original registered task `session:01a07158-684b-74a2-a47e-7ca0e91889b7` removed only that untracked source file, proved the old worktree pristine, and ran the merged ordinary `retire` command with expected HEAD `cd17e72a2e8e65c2a234439e6bfbc71943d99721`.
- The retirement returned `ok=true`, `status=retired`, `recovered_pending=null`. The old path is absent from the filesystem and Git worktree list. Its local and server branch refs both remain at `cd17e72a2e8e65c2a234439e6bfbc71943d99721`; the preserved external copy remains byte-exact; registry pending is null and its lock is absent.
- Package closure PR 963 passed required build 2647 and was accepted on main at `43fb592ff97b5e1490a40b2e027180969712808e`. The claim records the accepted mechanism merge SHA `9cf83d82f306a60486ca62764b5595bca76c2c2d`. No branch, tag, stash, or history was deleted, and no production or deployment action occurred.
