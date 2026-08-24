# PS-RELEASE-TRUTH-001 — delivery evidence

Runtime-inert record. Bounded path, writer self-review.

## Outcome

The repository now records the production state that actually exists.

Manual Azure run **1512** deployed main `5436e423b928f4f3d290e840c95c6a37528ce1c9`
with `forceProductionDeploy=true` and `schemaAction=none`, carrying the independently
reviewed `PS-WORKSHOP-PROVENANCE-001` fix. Live `/healthz` release is
`f21b9745e9e67d2ac958e586`.

Before this change `CURRENT_BASELINE.yaml` still recorded rollback commit
`00f73f86887d80645524626a0def44e52f79c9c9` from pipeline 1453 — a production state that
no longer existed. Baseline and its pinning test agreed with each other, so main stayed
green while both were factually stale.

## Verification

- **Release identity proved, not observed.** `release_id_for_build(5436e423…, "1512")`
  equals the live `/healthz` value exactly, so production serves precisely the deployed
  SHA. `tests/test_operational_readiness.py` recomputes the same value and asserts the
  baseline note carries it.
- **Stage evidence** read from the run 1512 timeline: the schema read/apply stages, both
  candidate stages, and both independently gated maintenance stages all **skipped**;
  the run carries **zero `Checkpoint.Approval` records**, so the schema approval path was
  untouched.
- **Lockstep honoured.** The baseline block and the test pointers move in this one commit.
- **Word cap.** Baseline measures 815 words against the <900 cap.
- **Tests.** 120 passed across every suite that reads the baseline
  (`test_control_room`, `test_governance_pointers`, `test_operational_readiness`,
  `test_package_registry`, `test_site_rules`).

## Honest limitations

- This records a release fact. It changes no runtime behaviour and deploys nothing.
- The Workshop provenance fix is live but **not live-proven**: confirming that accepting
  an AI rewrite now retains the member's own wording needs an authenticated session, which
  this task neither had nor should have had. `/app/workshop/work` was deliberately never
  loaded because its GET spends paid AI.
