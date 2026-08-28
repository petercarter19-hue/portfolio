# PS-WORKSHOP-USE-DISCLOSURE-PRODUCTION-TRUTH-001 — completion evidence

Runtime-inert Bounded delivery record. Production, deployment, schema,
identity-use, provider-use, and live-operation authority remain withheld. The
review time below is the writer-recorded UTC immediately after receipt of the
independent verdict.

## Outcome

The reviewed candidate records the already-completed Workshop D production
truth without changing runtime behaviour. `docs/governance/PRODUCTION_SCHEMA_STATE.md`
is copied byte-for-byte from run 1719 `SchemaMigrationEvidence`: production
`peerslate-database` carries `PS-OPPSLATE-USE-001`, the generated ledger count
is 29, and its SHA-256 is
`5f155d360ee6639c2c97e1eaa67968b9e116be02f55fe83c0e9deddb14e46328`.

`CURRENT_BASELINE.yaml` and its lockstep operational-readiness test now record
the separately deployed application source
`9e40993dce28fff7fc6697353c31a0352f775d5e`, manual run 1720, and live
`/healthz` release `039c8e24ad92c1e62ee883f2`. The record explicitly states
that no authenticated private live proof was performed.

Run 1719 applied only `PS-OPPSLATE-USE-001` at executable digest
`fe7e929fa12a32d9b0d4a78be04330b6e144ddf8c3ea8aff9fcf06016353374e`
after the exact one-item preflight and approval check 11, advancing the ledger
from 28 to 29. Run 1720 used `schemaAction=none`; its schema stages skipped
while build, deployment, and public smoke succeeded.

## Candidate and independent review

- Activation merge/base: `b19ae8c6791add6ac11f1e0357fe483c734e7c12`.
- Reviewed candidate: `3d1d81939f3bba8d45e4853006ed996521f44e8c`.
- Branch: `work/2026-08-28-workshop-use-disclosure-production-truth-001`.
- Writer: `agent:/root/workshop_sql_gate_release`.
- Independent reviewer: `agent:/root/production_truth_reviewer`.
- Writer-recorded receipt UTC: `2026-08-28T06:21:14Z`.
- Verdict: **unconditional PASS**, read-only, with no findings.

The reviewer independently verified the exact three-path candidate, run-1719
artifact byte identity and hash, migration digest and 28-to-29 ledger change,
run-1720 exact application source and `schemaAction=none`, recomputed release
identity, live `/healthz` match, the generated 29-applied plus 5-pending state,
the truthful absence of authenticated private proof, and the focused tests.

The reviewed candidate changes exactly:

- `docs/governance/CURRENT_BASELINE.yaml`
- `docs/governance/PRODUCTION_SCHEMA_STATE.md`
- `tests/test_operational_readiness.py`

Only this evidence file and its matching receipt are added after review; no
reviewed candidate byte changes.

## Verification

- `cmp` against run 1719's extracted
  `SchemaMigrationEvidence/PRODUCTION_SCHEMA_STATE.md` passed byte-for-byte;
  both files hash to
  `5f155d360ee6639c2c97e1eaa67968b9e116be02f55fe83c0e9deddb14e46328`.
- `release_id_for_build("9e40993dce28fff7fc6697353c31a0352f775d5e", "1720")`
  returned `039c8e24ad92c1e62ee883f2`.
- Ruby/Psych parsed `CURRENT_BASELINE.yaml`; it measured 809 words against the
  repository's under-900-word guard.
- In a disposable full-layout archive bound read-only to the candidate's Git
  metadata,
  `ANTHROPIC_API_KEY=test-placeholder PYTHONDONTWRITEBYTECODE=1 uv run --with-requirements requirements.txt python -B -m unittest tests.test_control_room tests.test_governance_pointers tests.test_operational_readiness tests.test_package_registry tests.test_schema_migration_path tests.test_site_rules`
  passed **170 tests, 0 failed**. The placeholder satisfied import validation;
  no provider was called.
- `git diff --check`, exact remote-tip proof, and the fetched clean write
  preflight passed.

Two earlier local harness invocations were discarded: the first lacked files
because the managed checkout is surface-sparse, and the first full archive
lacked Git identity. The corrected full-layout, Git-bound run above passed;
neither harness issue identified a candidate defect.

## Release state and boundaries

The schema and application release described here were completed earlier by
the separately authorized parent delivery. This bookkeeping package performed
no Azure, database, schema, deployment, identity, provider, or live operation.
At this evidence-tail state its reviewed repository candidate is pushed but not
yet merged. The next action is only its guarded PR, CI, squash merge, and claim
close. No authenticated private live proof is claimed.
