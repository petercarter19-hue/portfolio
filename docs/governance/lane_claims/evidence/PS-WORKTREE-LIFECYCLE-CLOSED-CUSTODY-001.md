# PS-WORKTREE-LIFECYCLE-CLOSED-CUSTODY-001 evidence

## Authority and release boundary

- Pete's owner authorization reference is
  `session:01a03e17-a645-7ae0-8da3-164eef90a333/pete-chat-2026-09-04/close-worktrees-cleanup-very-important`.
- The package is Protected, repository authority is `through_merge`, and
  production authority is withheld.
- The accepted implementation candidate is
  `d74a7072efe5777d431f15a5906ac447fa18c808` on
  `work/2026-09-04-worktree-lifecycle-closed-custody-001`.
- No target worktree was mutated before independent acceptance and merge. The
  execution sections below record the later per-target cleanup, cache custody,
  recovered bytes, and retained exceptions.

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
- Initial implementation PR 920 passed required CI 2459 and merged without
  bypass at `ce4e026f2f6af30c98525fcc8efbb8a762361899`. Read-only production-state
  proof then found that the released same-package control singleton was counted
  alongside the cleanup durable record. Final candidate `d74a7072...` narrows
  that initial lookup to active durable records while preserving independent
  exact-path ambiguity refusal across all record kinds and states.

## Validation

- Writer: `python3 -m py_compile scripts/worktree_lifecycle.py tests/test_worktree_lifecycle.py` — passed.
- Writer: six corrected-path closed-custody tests — 6 passed in 24.089 seconds.
- Writer: `python3 -B -m unittest tests.test_worktree_lifecycle` — 62 passed in
  105.331 seconds.
- Writer: `python3 -B -m unittest tests.test_delivery_preflight tests.test_package_registry -q`
  — 203 passed in 2.174 seconds.
- Writer after the production-state correction: six closed-custody tests passed
  in 29.479 seconds; all 62 lifecycle tests passed in 111.426 seconds; all 203
  delivery/registry tests passed in 2.186 seconds.
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
- Final candidate reviewed at: `2026-09-04T13:37:47Z`.
- Result: pass with no blocking findings.
- Exact final remote candidate, merge base, and tree were
  `d74a7072efe5777d431f15a5906ac447fa18c808`,
  `ce4e026f2f6af30c98525fcc8efbb8a762361899`, and
  `c479aaee7a55f6563ef7d69243911f2b1f80adfa`.
- Reviewer validation: seven focused corrected-path tests passed in 29.473
  seconds; all 62 lifecycle tests passed in 112.458 seconds; diff and forbidden-
  primitive checks passed.
- The review resolved all three blockers from rejected candidate
  `9272617d51e6f2f4a663249e2d3b624871c204ac`: pre-merge execution gating,
  complete present-side crash recovery proof, and exact previous-head journal
  binding.
- The final review also accepted the production-shaped same-package
  control-singleton correction with no blocking findings and no target
  mutation.

### Final close-sequencing review

- Reviewer:
  `agent:/root/closed_custody_implementation/closed_custody_review`.
- Reviewed at: `2026-09-04T14:31:19Z`.
- Result: pass with no blocking findings for exact candidate
  `46258986432e1f0ef76b7d7e493c4800b8b34df5`, tree
  `fc74e70518caf6b6f1d7aa9992256d434753f724`, direct parent
  `5011423709d5b8a14bb801bcb72970cde451ee37`, and current-main merge base
  `f073f5e75f145d12845f8ea9cba324bc914babe9`.
- The exact candidate delta is limited to this fixed evidence file and the
  claimed `docs/governance/WORKTREE_LIFECYCLE.md` close-sequencing
  clarification. The claim, receipt, implementation, tests, and
  `docs/governance/PACKAGE_REGISTRY.json` are byte-identical to the parent.
- Independent review reproduced the evidence-only close refusal, remeasured
  all Trash counts and bytes exactly, proved package and `_control` pristine
  with lease/pending null and lock absent, and confirmed the three Group-C
  worktrees still have their recorded HEAD splits and residue. It made no
  repository, registry, ref, cache, custody, target, or Group-C mutation.
- After current main advanced through the disjoint Azure merge, merge preflight
  correctly refused that earlier candidate because the later main merge was a
  non-evidence post-review branch delta. The reviewer therefore independently
  accepted the new exact branch-tip candidate
  `e808ce995f71bc3243e87b26a8d57da813b09578` at
  `2026-09-04T14:35:32Z`, tree
  `e63ea3ae975f002fec8fe3a825875635b7adb087`, against exact current main and
  merge base `84fbc1c148afe57738a44446b0fcc412d6e80ce1`. Its complete merge-base delta
  is only the claimed lifecycle document, fixed package evidence, and package
  receipt; its server-tip post-review delta is empty. All prior custody totals,
  package/control state, and Group-C preserve facts re-reconciled exactly, and
  the fresh review made no mutation.

## Protected merge and execution gate

- Initial PR 920 merged without bypass at
  `ce4e026f2f6af30c98525fcc8efbb8a762361899` after required CI 2459 succeeded.
- The production-state correction PR 921 merged without bypass at
  `4e4266403bf347bb19e644325150a1fc3c4b7943` after required CI 2463 succeeded.
- Before cleanup, fetched main, receipt candidate
  `d74a7072efe5777d431f15a5906ac447fa18c808`, cleanup branch, and executing
  script passed the exact reviewed-blob gate. Registry pending was null, the
  control lease was null, and `worktree_registry.lock` was absent.
- The first target attempt refused before journaling because the cleanup caller
  contained five ignored Python cache directories created by validation. The
  target was preserved. Those five proven ignored/untracked cache roots (19
  files, 5 directories, 939,889 logical bytes, 983,040 allocated-entry bytes)
  were moved with exact source/destination parity to the recoverable Trash
  custody root below. The cleanup worktree then re-proved pristine.

## Retired worktrees

Each row was freshly proved against its fetched closed claim and exact local,
live, and server HEAD, then retired in a separate ordinary non-force Git
transaction. Post-audit proved the path absent, the registry record retired,
the original `task_ref` retained, and both local and server branch refs still
at the expected SHA.

| Package | Expected HEAD | Recorded at (UTC) | Allocation (KiB) | Logical file bytes | Source-unavailability ref suffix |
|---|---|---:|---:|---:|---|
| `PS-SYNTHETIC-SEALED-AZURE-CLI-DARWIN-COMPAT-001` | `a153462ab3729352456d425f8daaa7a0ec0fd924` | `2026-09-04T13:49:46Z` | 951,440 | 967,027,915 | `azure-cli-darwin-compat` |
| `PS-SYNTHETIC-SEALED-AZURE-AUTH-SHAPE-001` | `1a2ee909b16b5298fac6dfce721fe61b55177a87` | `2026-09-04T13:50:23Z` | 952,256 | 967,772,938 | `azure-auth-shape` |
| `PS-SYNTHETIC-SEALED-GRAPH-PUBLIC-CLIENT-REBIND-001` | `da5ca9188857d7e4f22f75ae6a4fcd238b8e2314` | `2026-09-04T13:51:12Z` | 952,268 | 967,778,899 | `graph-public-client-rebind` |
| `PS-DELIVERY-OWNER-REASSIGNMENT-001` | `6f5bf17127ba93250ea14e016aec2a97222d5a9c` | `2026-09-04T13:52:05Z` | 50,060 | 50,506,311 | `delivery-owner-reassignment` |
| `PS-WORKSHOP-DELIVERY-CONTINUITY-001` | `80c421a101d6fec4c43993cd6ea3999131f61fa7` | `2026-09-04T13:52:49Z` | 49,944 | 50,390,743 | `workshop-delivery-continuity` |
| `PS-SYNTHETIC-SEALED-CREDENTIAL-BROKER-WINDOWS-CHILD-RUNTIME-001` | `88f05ad08ecc21cad46d8ef6ccc35f475cdb23db` | `2026-09-04T13:53:50Z` | 951,820 | 967,409,450 | `windows-child-runtime` |
| `PS-WORKSHOP-FG-AUTHENTICATED-PROOF-TRUTH-001` | `8c4cf881d1b3e6ec1a08c1737345c9eda2d333b5` | `2026-09-04T13:54:38Z` | 952,664 | 968,186,482 | `fg-authenticated-proof-truth-001` |
| `PS-WORKSHOP-FG-AUTHENTICATED-PROOF-TRUTH-002` | `3d1948f07485a421fd3c0a95dfff09a0f82f1ae7` | `2026-09-04T13:55:29Z` | 952,892 | 968,386,022 | `fg-authenticated-proof-truth-002` |
| `PS-AZURE-STARTUP-QUALIFICATION-001` | `421caa561a2c6d40553c07660ef58cf712f26e43` | `2026-09-04T13:56:45Z` | 971,980 | 986,812,577 | `azure-startup-qualification` |
| `PS-CI-SECRET-SCAN-ALLOWLIST-001` | `98f72b3ec5c8e66a307e3ee3344078e4c74b8af4` | `2026-09-04T13:57:57Z` | 962,708 | 977,845,409 | `ci-secret-scan-allowlist` |

The common prefix for every last-column reference is
`session:01a03e17-a645-7ae0-8da3-164eef90a333/closed-custody/unavailable/`.
The 10 retired worktrees total 7,748,032 allocated KiB, or 7,933,984,768
allocated-entry bytes, and 7,872,116,746 logical file bytes. These values were
captured before each ordinary removal; no prune or garbage collection ran.

## Recoverable cache custody

Only ignored cache roots with zero tracked files and zero nonignored residue
were moved. Each target then re-proved fully pristine before retirement. Source
and Trash destination measurements matched exactly.

Trash root:
`/Users/petercarter/.Trash/PeerSlate-closed-custody-2026-09-04-d74a7072`

| Package | Cache roots | Files | Directories | Logical bytes | Allocated-entry bytes |
|---|---:|---:|---:|---:|---:|
| `PS-WORKTREE-LIFECYCLE-CLOSED-CUSTODY-001` | 7 | 21 | 7 | 1,558,835 | 1,605,632 |
| `PS-DELIVERY-OWNER-REASSIGNMENT-001` | 2 | 11 | 2 | 978,069 | 999,424 |
| `PS-WORKSHOP-DELIVERY-CONTINUITY-001` | 2 | 5 | 2 | 835,051 | 843,776 |
| `PS-SYNTHETIC-SEALED-CREDENTIAL-BROKER-WINDOWS-CHILD-RUNTIME-001` | 6 | 7 | 6 | 404,702 | 417,792 |
| `PS-WORKSHOP-FG-AUTHENTICATED-PROOF-TRUTH-001` | 3 | 5 | 3 | 419,649 | 430,080 |
| `PS-WORKSHOP-FG-AUTHENTICATED-PROOF-TRUTH-002` | 3 | 5 | 3 | 420,823 | 430,080 |
| `PS-AZURE-STARTUP-QUALIFICATION-001` | 16 | 505 | 19 | 18,334,062 | 19,398,656 |
| `PS-CI-SECRET-SCAN-ALLOWLIST-001` | 13 | 256 | 13 | 9,361,776 | 9,904,128 |
| **Total** | **52** | **815** | **55** | **32,312,967** | **34,029,568** |

The Trash tree contains the same 815 files and 32,312,967 logical file bytes.
Including custody parent directories, it has 118 directories and 34,029,568
allocated-entry bytes. The payload remains recoverable; nothing was deleted.

After the evidence-only cleanup result was merged, the first formal close
preflight correctly refused because the receipt candidate contained only the
package evidence path once evidence and receipt tails were excluded. No claim
close was merged. The `_control` lease was released cleanly, and its one proven
ignored Python cache file was moved to a distinct `_control` custody path with
exact source/destination parity (309,457 logical bytes; 311,296 allocated-entry
bytes). A later exact pre-retirement check found one proven ignored Python
cache file in the cleanup worktree; it was likewise moved to a distinct
`cleanup-final` custody path with parity (309,489 logical bytes; 311,296
allocated-entry bytes). The row and totals above include both additions. All
subsequent Python lifecycle and preflight invocations use bytecode suppression
so the final worktree remains pristine.

## Deliberately retained preserve cases

The following three worktrees were rechecked read-only and were not reset,
cleaned, fast-forwarded, cache-moved, removed, or otherwise mutated:

- `PS-SYNTHETIC-SEALED-GRAPH-DELETION-001`: present with seven tracked
  modifications and an ignored cache; live/local HEAD
  `c7122dc69421014155643568f231616206170eb1` differs from server HEAD
  `61de8ed7ffc46d961597c0bf8fdf602cfba9b5c9`.
- `PS-SYNTHETIC-SEALED-GRAPH-DELETION-CORRECTION-001`: present with an ignored
  cache; live/local HEAD `f0a919d05db7983329fc1eff1fdf00c76540c2ec`
  differs from server HEAD `7d0e95e9e5191b31afd85f04fd80263765831c9b`.
- `PS-SYNTHETIC-SEALED-GRAPH-PUBLIC-CLIENT-001`: present with four tracked
  modifications, one untracked lock file, and two ignored caches; live/local
  HEAD `d80f2a885ba90e5eed9f3fbd148e133806b2af48` differs from server HEAD
  `1e62ee370eec9b4f9c55be977851ef2fa14a3fc5`.

Final local registry proof after all safe retirements: pending null, registry
lock absent, 10 exact retired custody records, and every retirement proof bound
to final reviewed candidate `d74a7072efe5777d431f15a5906ac447fa18c808`
and authoritative main `4e4266403bf347bb19e644325150a1fc3c4b7943`.
