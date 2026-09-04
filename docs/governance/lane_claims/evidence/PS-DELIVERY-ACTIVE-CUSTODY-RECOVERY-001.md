# PS-DELIVERY-ACTIVE-CUSTODY-RECOVERY-001 — completion evidence

Runtime-inert Protected Delivery Control record. Production authority remains
withheld. This package supplies a fail-closed custody mechanism; it does not
perform either later product-package owner reassignment.

## Outcome

The lifecycle tool now recognizes the repository's governed `superseded`
claim state as terminal and excludes it from live ownership enumeration. It
does not weaken the delivery preflight's full superseded-claim validation or
its reserved-branch behavior.

Owner-reassignment preparation can now reconcile one stale machine-local
active-durable registry HEAD only when a separately named bounded
source-unavailability evidence reference and the owner's exact authorization
are present. The active claim, original task, source branch, canonical managed
path, no source lease, pristine live checkout including ignored files, local
branch, and freshly fetched server tip must all identify one checkpoint. The
old recorded HEAD must be its Git ancestor. Duplicate records, residue,
divergence, ambiguity, locks, pending operations, moved refs, or races refuse.

The correction and absent-successor creation use one atomic before/after
journal. If the successor remains absent, immediate or crash recovery restores
the complete prior registry record before clearing the journal. If Git proves
one exact new branch, final proof repeats the authoritative tuple before the
reconciled record and completed preparation are committed together. The
source-unavailability proof is retained in the preparation's digest-bound
immutable fields. Every proof-bearing record has an exact bidirectional link
to one pending journal or completed/consuming/consumed preparation; stripped,
orphan, reused, or explicit-null proof state refuses before recovery. A later
original-writer `ensure` cannot advance reconciled custody after preparation.

Normal equal-HEAD reassignment and the pre-existing no-durable-source path are
unchanged. The source checkout and old branch bytes are never changed. This
package adds no reset, clean, removal, prune, garbage collection, ref deletion,
claim close, closed-worktree retirement, product code, deployment, schema,
identity, or production action.

## Candidate and independent review

- Activation main: `c6f7af9a5678b0abee57239e017cc0eea81c68ef`.
- Reviewed candidate: `01479d66db83dc453291a8b44e5860cb1d3b1744`.
- Branch: `work/2026-09-04-delivery-active-custody-recovery-001`.
- Writer: `agent:/root/active_custody_recovery`.
- Primary independent reviewer:
  `agent:/root/active_custody_recovery/active_custody_exact_sha_review`.
- Second independent reviewer: `agent:/root/custody_recovery_second_review`.
- Writer-recorded review receipt UTC: `2026-09-04T09:37:40Z`.
- Final verdict: **PASS**, read-only, with no blocking findings from either
  reviewer.

The exact reviewed diff changes five claimed paths: `AGENTS.md`,
`START_HERE.md`, `docs/governance/WORKTREE_LIFECYCLE.md`,
`scripts/worktree_lifecycle.py`, and `tests/test_worktree_lifecycle.py`. It is
1,114 insertions and 6 deletions: 481 lifecycle implementation lines, 578
positive/adversarial/regression test lines, and 55 governance-document lines.
The size is driven by the existing crash-safe journal model: exact before/after
record schemas, validation, rollback and final-boundary proof, immutable
completed custody, and comprehensive poison/race compatibility coverage. It
does not introduce a general registry rewrite or broader custody exception.

The first reviewer rejected an earlier candidate because reference separation
was not revalidated after persistence. The second reviewer then reproduced a
stripped-pending-journal path that could strand a reconciled record, and the
first reviewer identified a documentation mismatch. Final writer self-review
also rejected present-null proof keys. Each issue was corrected and retested;
all earlier candidate SHAs are ineligible.

## Verification

- Writer: `python3 -B -m unittest -v tests.test_delivery_preflight
  tests.test_worktree_lifecycle` — **257 tests passed in 90.019 seconds; OK**.
- Primary reviewer: the same combined suite — **257 tests passed in 92.118
  seconds; OK** — plus four focused recovery checks and direct persisted-proof
  poison probes.
- Second reviewer: **56 lifecycle tests** and **6 focused adversarial checks;
  OK**, including the stripped-journal reproducer.
- `git diff --check` — passed.
- Exact local HEAD, Azure remote branch, and tracking ref all matched the
  reviewed candidate; the worktree was pristine.
- The strict current-`origin/main` claim read accepted the governed terminal
  Settings supersession and returned only the three then-active claims.
- Protected write preflight passed on the clean reviewed candidate.

## Release boundary

The candidate is independently accepted and pushed. At this evidence-tail
state it is not yet merged, deployed, or production-live. Merge remains subject
to the normal clean exact-SHA merge preflight, Azure PR policy, successful CI,
and a separate close transition. Repository rollback, if ever required, is an
ordinary reviewed revert; this package has no deployment or schema rollback.
