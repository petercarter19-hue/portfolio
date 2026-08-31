# PS-DELIVERY-SIMPLIFICATION-CLOSE-REPAIR-001 — evidence

Runtime-inert completion evidence. Owner authorization:
`pete-chat-2026-08-31/central-five-item-cleanup-handoff`.

## Outcome

Close scope validation now recognizes exactly one already-reviewed,
already-merged historical tuple so that PS-DELIVERY-CONTROL-SIMPLIFICATION-001
can be closed truthfully:

- package: `PS-DELIVERY-CONTROL-SIMPLIFICATION-001`
- reviewed candidate: `ff3959815f3e4a9ca4dc5dd404a42a5e11ec462a`
- implementation merge: `1b6b5d4905af32edfee43c02d6e2bdb58d31898c` (PR 593)
- tolerated paths (the two legacy bootstrap records that candidate created
  while introducing the per-package claim model itself):
  - `docs/governance/lane_claims/PS-SYNTHETIC-MULTI-MEMBER-QA-001.json`
  - `docs/governance/lane_claims/receipts/PS-SYNTHETIC-MULTI-MEMBER-QA-001.json`

The tolerance applies only to the close intent's scope-error list. The
tolerated paths remain fully subject to byte identity, merged-path
introduction, receipt verification, and branch preservation. Every other
package, candidate, merge, and path keeps strict behavior. No generic bypass,
waiver, wildcard, or configurable exception mechanism exists.

## Delivery record

- Base: `bd95f1e4d3b90a2f0e40756795010ff9db4d0af0` (origin/main at activation)
- Reviewed candidate: `05a7ae8a76670ff0dc718210bd2cbc3f0b37a7ad`
- Changed paths: `scripts/delivery_preflight.py`,
  `tests/test_delivery_preflight.py`
- Validation: `tests.test_delivery_preflight` 136 tests OK (including seven
  new positive/adversarial tests: exact tuple passes; wrong package, wrong
  candidate, wrong merge, smuggled additional path, missing receipt, and
  byte mismatch each still fail); `tests.test_governance_pointers` OK;
  `tests.test_worktree_lifecycle` and
  `tests.test_production_operation_preflight` OK.
  `tests.test_operational_readiness` requires the application virtualenv and
  runs in PR CI.
- Review: independent read-only exact-SHA review, result PASS, reviewer
  `session:9547fc3c-1d26-4689-abbf-61641eae154a/simplification-close-repair-independent-reviewer`;
  two informational findings, none blocking (see receipt).
- The reviewer independently re-derived the historical tuple from
  origin/main, confirmed exactly two out-of-claim paths in the historical
  candidate diff, and confirmed `git diff ff395981..1b6b5d49` is empty for
  both tolerated paths (candidate-identical bytes at the historical merge).

## Honest limits

- The exception is intentionally unreusable; any future historical repair
  needs its own reviewed code change through the same governed path.
- No product, production, schema, identity, or Synthetic behavior changed.
