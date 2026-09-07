# PS-HISTORICAL-CHECKOUT-RETIREMENT-002 candidate evidence

## Authority and boundary

- Owner outcome: `session:01a07158-684b-74a2-a47e-7ca0e91889b7/owner-finish-2026-09-07`.
- Writer: `agent:/root/historical_writer`.
- Delivery: Protected, repository authority through accepted merge, production withheld, independent review required.
- This package replaces paused partial-transfer package
  `PS-HISTORICAL-CHECKOUT-RETIREMENT-001`. Package 001, its worktree, branch,
  refs, and untracked handoff file remain preserved until this package closes.
- The only cleanup targets are the 29 immutable tuples in the package allowlist.
  No ref deletion, force removal, raw recursive deletion, pruning, garbage
  collection, reset, clean, history rewrite, production, deployment, schema,
  identity, product, or visual action is admitted.

## Candidate behavior

- Adds `retire-historical`, which removes one exact allowlisted historical Git
  worktree through ordinary non-force `git worktree remove`.
- Requires the executing lifecycle script and shared lifecycle surfaces to be
  the independently reviewed bytes accepted on fetched main.
- Requires the package allowlist, active claim, and this evidence file to be
  ordinary Git blobs with identical bytes at the reviewed candidate, fetched
  main, and cleanup branch HEAD.
- Requires the accepted review receipt to be an ordinary identical blob on
  fetched main and cleanup HEAD, and retains that blob identity in the crash
  recovery proof without creating a circular candidate dependency.
- Re-proves exact grandfathered registry custody, canonical path, live
  worktree, attached branch, local ref, server tip, cleanliness including
  ignored files, nesting, reparse safety, protected-claim exclusions, and
  unique live path-or-branch custody, and terminal main/cleanup/target server
  state while holding the registry mutex.
- Preserves an immutable before/after registry proof and limits crash recovery
  to the same caller and reviewed request. It preserves a still-present target
  and publishes an absent target only from the retained journal.
- Coexists with the current control-custody transition history and monotonic
  lease-clock validation.

## Validation

- Fresh write preflight: pass at base
  `3e629e10c017ab14c698472cd7d7dcceeff6ea2a`; only 58 unrelated
  grandfathered observations were warnings.
- Allowlist revalidation: 29/29 targets passed against the current registry,
  Git worktree list, live branch and HEAD, local refs, server tips, strict
  tracked/untracked/ignored cleanliness, nesting, reparse, and protected-claim
  exclusions; 0 issues.
- Focused historical retirement tests: 12/12 passed in 189.344 seconds. These cover ref/tag/stash
  preservation, control registry coexistence, request and registry drift,
  tracked/untracked/ignored residue, nested/detached/reparse refusal,
  active/paused/superseded claims, local-ref and remote-tip drift, claim and
  evidence byte drift, main/cleanup receipt absence or byte drift,
  manifest/mechanism drift, duplicate JSON, duplicate path or branch custody,
  crash recovery, and journal/caller poisoning.
- Full lifecycle suite: 97/97 passed in 1272.265 seconds with
  `PYTHONDONTWRITEBYTECODE=1 python -B -m unittest tests.test_worktree_lifecycle`.
- Syntax parses passed for both lifecycle implementation and tests.
- `git diff --check`: pass.

No historical worktree has been retired by this candidate. Retirement remains
blocked until this exact candidate receives a separate independent pass, the
receipt and candidate are accepted on main, and every action-time gate passes.
