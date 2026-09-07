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
