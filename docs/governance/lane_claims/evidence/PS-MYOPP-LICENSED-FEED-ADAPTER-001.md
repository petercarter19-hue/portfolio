# PS-MYOPP-LICENSED-FEED-ADAPTER-001 review evidence

Runtime-inert review-tail record for the Protected C11 licensed-feed-adapter
package. The paired receipt is
`docs/governance/lane_claims/receipts/PS-MYOPP-LICENSED-FEED-ADAPTER-001.json`.

## Scope and authority

- **Package boundary:** one provider-neutral adapter core on C2's
  describe/acquire/normalize contract, with licensed-aggregator,
  government-feed, and direct-employer variants; documented-format fictional
  fixtures and tests; strict settings bindings; live source-policy and
  point-of-use rights enforcement; bounded retry, rate, error, and wall-clock
  behavior; and termination, removal, and exit rehearsals.
- **Authority:** `repository_authority: through_merge` and
  `production_authority: withheld`. This tail records repository review
  evidence only. It confers no provider, legal, contract, account, credential,
  spend, network, live acquisition, policy-seeding, migration, deployment,
  enablement, scheduling, cutover, or production authority.
- **Owner outcome:** Pete's recorded include-all provider-options decision,
  `session:4b21c2ac-0236-4dc0-af54-2c15e6f126ce/pete-chat-2026-09-01/include-all-provider-options`.

## Frozen candidate

Independent reviewer `agent:/root/myopp_c11_impl/c11_independent_review`
reviewed exact pushed candidate
`0007dd5210f0ae0cc4e478b70fc15e2075ba3116` read-only on branch
`work/2026-09-01-myopp-licensed-feed-adapter-001`, with merge base
`9813ef8caea9a4984481397daf2044dd1cf1d59e`. The implementation writer is
`agent:codex/2026-09-02/myopp-c11-writer`; writer and reviewer are distinct.
The reviewer returned **ACCEPT** with no blocking or material findings.

At review time the candidate was four commits ahead and one commit behind
`origin/main`. The only main-only path was the disjoint C13 claim
`docs/governance/lane_claims/PS-MYOPP-URL-FETCH-001.json`; no overlapping
candidate surface had advanced. The branch and remote branch tip both resolved
to the exact candidate, and the worktree was clean.

## Review history and resolution

Three earlier exact candidates were rejected and superseded rather than
mutated after review:

- Candidate 1 was rejected during adversarial review.
- Candidate 2 was rejected during adversarial review.
- Candidate 3, `07a8097e6353a9818b8ef0feca6e0a6574929bb0`, corrected evidence
  extraction to retain exact contiguous JSON item-token slices, isolated
  malformed siblings and removals, enforced a strict direct-board JSON
  setting, and denied storage/display after termination. Independent review
  then found three remaining blockers: a direct-employer public-constructor
  registration bypass, termination-set mutation before complete semantic
  prevalidation, and no per-request remaining-time contract for a future live
  sender.

Candidate 4 resolved all three blockers. Production direct-employer
construction now rejects a caller-supplied employer and derives the identity
only from the validated named setting. Termination prevalidates the policy and
entire unique listing set before publishing a revision, rejects missing,
foreign, wrong-policy, wrong-class, and invalid terminal entries without
partial mutation, and supports exact-revision resume after interruption.
Every live request now carries a positive finite remaining timeout;
`LiveTransport` rejects an overdue return, and the documentation accurately
requires the future C9 sender to enforce that timeout during I/O rather than
claiming preemption of an arbitrary synchronous callable.

The final independent review reproduced both valid/missing termination
orderings, foreign-source and terminal-key failures, interrupted-revision
resume, completed replay, post-termination stop-before-transport, public
constructor override refusal, normal setting-derived construction, invalid
timeout refusal, positive remaining-time propagation, and one-call
budget-exhaustion after an overdue sender. It also reran the item-slice
regression: whitespace, ordering, escapes, and numeric spelling remained
byte-identical and the token appeared exactly once in its provider envelope.

## Verification

- `git diff --check` passed for both the Candidate-3-to-Candidate-4 delta and
  the full merge-base-to-candidate diff.
- The focused C11 suite passed: **56 tests**.
- The combined C11 plus C2 boundary suite passed: **100 tests** across
  `tests.test_my_opportunities_licensed_feed_adapter`,
  `tests.test_my_opportunities_canonical`,
  `tests.test_my_opportunities_ingestion`, and
  `tests.test_my_opportunities_safe_outbound`.
- The writer's combined boundary plus registry run passed: **102 tests**.
- The repository discovery run on Candidate 3 completed **2,365 tests** with
  no C11 failure, 3 skips, and 113 pre-existing collection errors caused by
  absent optional dependencies (`flask`, `anthropic`, `mssql_python`,
  `dotenv`, and `requests`). Candidate 4's changed boundary was then covered by
  the green focused and combined runs above.
- Targeted secret scanning, Python bytecode compilation, and worktree
  cleanliness checks passed.

## Limitations and post-review tail

No live source, provider, network, credentials, real inventory, policy seed,
migration, deployment, scheduling, enablement, or production operation was
used or claimed. Licensed aggregation stays fail-closed-empty without a
provider packet; government live use awaits written approval; direct live use
awaits per-employer registration. Fixtures are documentation-transcribed and
fictional. Future C9 transport must enforce each request's remaining timeout
during I/O.

The only files added after frozen candidate
`0007dd5210f0ae0cc4e478b70fc15e2075ba3116` are this evidence record and its
matching receipt. No reviewed implementation, test, fixture, README,
completion report, package registry, or claim byte changed in the post-review
tail. Merge preflight and any PR must remain bound to the exact candidate SHA.
