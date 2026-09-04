# PS-WORKTREE-LIFECYCLE-CLOSED-CUSTODY-001 evidence

## Authority and release boundary

- Pete's owner authorization reference is
  `session:01a03e17-a645-7ae0-8da3-164eef90a333/pete-chat-2026-09-04/close-worktrees-cleanup-very-important`.
- The package is Protected, repository authority is `through_merge`, and
  production authority is withheld.
- The accepted implementation candidate is
  `02a543d987a6a53235ac0355a6acf40ef96183bd` on
  `work/2026-09-04-worktree-lifecycle-closed-custody-001`.
- This evidence records implementation and review only. No target worktree was
  mutated before independent acceptance and merge. Per-target cleanup results,
  cache custody, recovered bytes, and retained exceptions will be appended
  after the reviewed mechanism is merged and used.

## Implemented contract

- Adds a distinct `retire-closed-custody` command for one fetched, exactly
  closed durable target whose original task is unavailable.
- Requires the active cleanup claim's exact Protected policy, writer, owner
  authorization, current worktree, branch, local HEAD, and server HEAD.
- Requires an accepted independent-pass receipt and evidence on fetched main,
  exact reviewed lifecycle surface blobs on the candidate, main, and cleanup
  branch, and the executing script blob equal to reviewed main.
- Requires exact target package, original task reference, canonical managed
  path, branch, live/local/server expected HEAD, pristine tracked/untracked/
  ignored state, no lease, no duplicate, no nesting, no reparse point, and no
  unrelated pending journal. A stale registry HEAD is admitted only when equal
  to or ancestral to the expected HEAD.
- Journals exact before/after records. Present-side recovery re-proves the full
  target identity before clearing a preserved journal, and every mismatch
  retains the journal. The retired record keeps the original `task_ref` and
  records the cleanup caller and evidence references separately.
- Uses one shared ordinary non-force `git worktree remove` primitive. It does
  not reset, clean, force, prune, run garbage collection, delete a branch/tag/
  ref, or deploy.

## Validation

- Writer: `python3 -m py_compile scripts/worktree_lifecycle.py tests/test_worktree_lifecycle.py` — passed.
- Writer: six corrected-path closed-custody tests — 6 passed in 24.089 seconds.
- Writer: `python3 -B -m unittest tests.test_worktree_lifecycle` — 62 passed in
  105.331 seconds.
- Writer: `python3 -B -m unittest tests.test_delivery_preflight tests.test_package_registry -q`
  — 203 passed in 2.174 seconds.
- Writer: `git diff --check` and exact forbidden-primitive scan — passed; one
  literal ordinary worktree removal primitive and no force/reset/clean/prune/
  garbage-collection/ref-deletion primitive.
- A full bare local unittest discovery was additionally attempted: 2,483 tests
  loaded and 116 import errors were reported because that local interpreter
  lacks repository runtime dependencies including Flask, Anthropic, dotenv,
  `mssql_python`, requests, and Werkzeug. No closed-custody or governance test
  failed; the dependency-provisioned protected CI remains the release gate.

## Independent review

- Reviewer:
  `agent:/root/closed_custody_implementation/closed_custody_review`.
- Reviewed at: `2026-09-04T13:17:01Z`.
- Result: pass with no blocking findings.
- Exact remote candidate, merge base, and tree were
  `02a543d987a6a53235ac0355a6acf40ef96183bd`,
  `69d94cc0ac903c1d76be052ca7450d5e996c99c0`, and
  `2eec6907e0fca34f863fd7c75b299b47a7317a79`.
- Reviewer validation from an immutable non-worktree archive: seven focused
  corrected-path tests passed in 24.832 seconds; all 62 lifecycle tests passed
  in 110.051 seconds; diff and forbidden-primitive checks passed.
- The review resolved all three blockers from rejected candidate
  `9272617d51e6f2f4a663249e2d3b624871c204ac`: pre-merge execution gating,
  complete present-side crash recovery proof, and exact previous-head journal
  binding.
