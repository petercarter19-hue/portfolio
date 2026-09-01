# PS-DELIVERY-SUPERSEDE-DISPOSITION-001 — evidence

Runtime-inert completion evidence. Owner authorization:
`pete-chat-2026-08-31/central-five-item-cleanup-handoff`.

## Outcome

Delivery governance now has one truthful terminal disposition — `superseded`
— for an activated-but-unmerged package that was rejected and replaced or
withdrawn, applied through the new `supersede` control transition. It is
semantically distinct from `closed`: nothing was delivered, `merged_sha` and
`closed_at` are forbidden, the preserved pushed checkpoint is mandatory, and
the claim branch name stays reserved because the unmerged bytes exist only
on that preserved remote branch.

The transition requires: the leased `_control` singleton on a dedicated
`delivery-supersede` branch; `--owner-authorization-ref` equal to the
claim's `supersession.owner_authorization_ref`; a paused origin claim; a
delta of exactly `{state, superseded_at, supersession}`; receipt absence on
origin/main; exact closed replacement package references or an exact
withdrawal reason; a fetched claim-branch tip equal to the preserved
checkpoint and not reachable from origin/main; and full prospective
claim-set validation. Superseded claims are terminal: resume, close, pause,
transfer, extend-surfaces, and write all refuse them, and the package path
cannot be re-activated.

## Delivery record

- Base: `336d677fd6b9f8ea9726e9bb2df451b897701826` (origin/main at branch)
- Reviewed candidate: `80e8a3c52d61b1e55ab086e1af35443408b73ce3`
  (round-1 candidate `61c9403ad4d3c2f2c706f2d01b10be5b0c9c1ef4` plus the
  one-hunk review correction)
- Changed paths: `scripts/delivery_preflight.py`,
  `tests/test_delivery_preflight.py`, `START_HERE.md`
- Validation: `tests.test_delivery_preflight` 201 tests OK (14 new
  positive/adversarial tests across claim validation, the supersede intent,
  terminality, and branch reservation); `tests.test_governance_pointers`
  25 OK; `tests.test_worktree_lifecycle` and
  `tests.test_production_operation_preflight` 60 OK.
  `tests.test_operational_readiness` requires the application virtualenv
  and runs in PR CI.
- Review: independent read-only exact-SHA review in two rounds, result
  PASS, reviewer
  `session:9547fc3c-1d26-4689-abbf-61641eae154a/supersede-disposition-independent-reviewer`;
  one LOW finding (stale argparse help text) corrected and re-verified;
  informational notes carried in the receipt.

## Honest limits

- The supersede gates rely on the standing repository invariants that
  governed merges always leave receipts and that main refuses direct
  pushes; a compound upstream governance breach is outside this package's
  threat model (recorded in the receipt).
- No product, production, schema, identity, or Synthetic behavior changed.
