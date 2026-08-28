# PS-WORKSHOP-FG-PRODUCTION-TRUTH-001 — completion evidence

Runtime-inert Bounded delivery record. Production, deployment, schema,
identity-use, provider-use, and live-operation authority remain withheld.

## Outcome

The reviewed candidate records the already-completed Workshop F and G
production truth without changing runtime behaviour.
`docs/governance/PRODUCTION_SCHEMA_STATE.md` is copied byte-for-byte from run
1759 `SchemaMigrationEvidence`: production `peerslate-database` carries
`PS-WORKSHOP-003` and `PS-WORKSHOP-004`, the generated ledger count is 31, and
the file's SHA-256 is
`c7529188318c7c9050b9b5022cbd9d3ed0813826ca57db3945eb47953a541a84`.

Run 1758 applied only `PS-WORKSHOP-003` at executable digest
`18e764fbc15cdfe3f00c54d318e48067dad97430afcf8df2fe685fc396708736`
after its exact one-item preflight and approval check 11, advancing the ledger
from 29 to 30. Run 1759 then applied only `PS-WORKSHOP-004` at executable
digest
`53561ce3275599cd7d4f34c234a8455313ac82d1d967194f449d9e25e7c2fcba`
after its own exact one-item preflight and approval, advancing the ledger from
30 to 31. Run 1759 was `partiallySucceeded` only because its post-apply
repository-state comparison saw the expected stale pre-W3 committed state;
the same-run apply evidence proves the W4 application and 30-to-31 result.
Both approval comments bind Pete's exact delegated owner reference and record
that the release operator authenticated as the environment's sole approver,
so no independent separation of duties is claimed.

`CURRENT_BASELINE.yaml` and its lockstep operational-readiness test record the
separate schema-none web deployment from source
`ebc702870abbc0b56240cb43a7f34fa06d251fcd`, manual run 1761, and live
`/healthz` release `de34c238cb406a6b8c5d4c08`. Build, the exact-operation
guard, the live Community schema prerequisite, deployment, and public smoke
succeeded; schema, Candidate, independently gated maintenance, retention, and
not-deployed branches skipped.

An anonymous `GET /app/workshop` returned HTTP 200 with `no-store, private`
caching and explicitly labeled the visible Jordan Ellis content as temporary
example-member data that is not the visitor's and lasts only for the public
session. No authenticated two-member private live proof was performed; that
proof remains pending and must not be inferred from the anonymous check.

## CI correction and reviewed candidate

The first three-path candidate `3bd5401a0628e8e17f7207f2c8a6e0a56c644e51`
received an independent pass on its reviewed scope, but PR 677 validation run
1764 correctly stopped the merge with one failure among 4,215 tests:
`test_current_production_ledger_plus_workshop_003_selects_w3_for_rollback`
still assumed W3 was the byte-exact production tip. No retry, duplicate run,
bypass, or merge occurred.

The writer used the guarded `extend-surfaces` flow to append only
`tests/test_workshop_provenance_visibility_migration.py`. Control PR 678 CI run
1765 passed and its one-claim change squash-merged as
`6931e7cde130200d0ac1c90eab7dff1222bc6779`. The implementation branch merged
that exact current main normally, removed the obsolete evidence and receipt,
and corrected only the newly claimed test: it now asserts W4 as the live
production tip, then removes W4 from a prior-ledger fixture and still proves
W3 is selected as that earlier rollback tip.

- Reviewed base: `6931e7cde130200d0ac1c90eab7dff1222bc6779`.
- Reviewed candidate: `6787d9d3fcb769daf6ff715e44f25afd017a9282`.
- Branch: `work/2026-08-28-workshop-fg-production-truth-001`.
- Writer: `agent:/root/workshop_fg_release`.
- Independent reviewer: `agent:/root/workshop_fg_truth_reviewer_r2`.
- Reviewer-recorded UTC: `2026-08-28T14:46:42Z`.
- Verdict: **unconditional PASS**, read-only, with zero findings.

The fresh reviewer verified the exact four-path diff, byte-equal final schema
artifact, W3 and W4 run/digest/ledger facts, W4-tip and W3 prior-ledger rollback
semantics, schema-none application release identity, anonymous disclosure,
pending authenticated-proof boundary, full test result, and clean fetched
write gate.

The reviewed candidate changes exactly:

- `docs/governance/CURRENT_BASELINE.yaml`
- `docs/governance/PRODUCTION_SCHEMA_STATE.md`
- `tests/test_operational_readiness.py`
- `tests/test_workshop_provenance_visibility_migration.py`

Only this rewritten evidence file and its matching receipt are added after the
fresh review; no reviewed candidate byte changes.

## Verification

- `cmp` against run 1759's extracted
  `SchemaMigrationEvidence/PRODUCTION_SCHEMA_STATE.md` passed byte-for-byte;
  both files hash to
  `c7529188318c7c9050b9b5022cbd9d3ed0813826ca57db3945eb47953a541a84`.
- Both same-run schema preflight ZIPs were valid and reported no blockers,
  one-item plans, and ledger counts 29 for W3 and 30 for W4. Both same-run
  apply ZIPs were valid and recorded the exact expected migration, digest,
  and ledger transition.
- Run 1761 was pinned to exact source
  `ebc702870abbc0b56240cb43a7f34fa06d251fcd` with
  `forceProductionDeploy=true`, the matching manual source, Pete's exact
  authorization reference, and `schemaAction=none`; it completed
  `succeeded`. `release_id_for_build` for that source and build 1761 returned
  `de34c238cb406a6b8c5d4c08`, matching live `/healthz`.
- Ruby/Psych parsed `CURRENT_BASELINE.yaml`; it measured 865 words against the
  repository's under-900-word guard.
- In a full-layout archive of exact candidate `6787d9d3`, the
  pipeline-equivalent Python 3.12 command
  `ANTHROPIC_API_KEY=test-key-for-ci-only uv run --python 3.12 --with-requirements requirements.txt python -B -m unittest discover -s tests -q`
  ran 4,215 tests with zero failures and 24 skips. The governed migration
  registry check passed all 36 entries, including 23 matching gate proofs.
- Existing PR 677 validation run 1768 succeeded against the exact candidate
  and current target merge ref before this runtime-inert evidence tail.
- `git diff --check`, exact remote candidate-tip proof, lifecycle audit, and
  the fetched clean write preflight passed.

One initial full-suite harness invocation was discarded because inherited
`GIT_DIR` and `GIT_WORK_TREE` polluted nested lifecycle test repositories. The
corrected run used no inherited Git environment and passed. Its temporary Git
binding was removed, the common repository configuration and sparse checkout
were restored and re-audited, and the registered durable-worktree write gate
then passed; the harness issue changed no candidate byte.

## Release state and boundaries

The schema and application release described here was completed earlier by
the separately authorized production delivery. This bookkeeping package
performed no Azure, database, schema, deployment, identity, provider, or live
mutation. The reviewed repository candidate is pushed; the next action is only
the existing PR's fresh current-target CI, squash merge, exact-main automatic
CI proof, and claim close.

Authenticated two-member private proof remains pending. It requires confirmed
ordinary attended QA identities and a separate Protected proof package; no
personal, administrative, synthetic, or anonymous substitute is claimed.
