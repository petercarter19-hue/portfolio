# Disposable x64 Community SQL CI harness checkpoint

## Outcome

Pete's 2026-08-02 instruction to keep going authorized the local preparation
needed to get past the Apple Silicon SQL-runtime blocker. The resulting harness
is implemented and passes local static/unit review. It remains inert by
default, is not connected to `azure-pipelines.yml`, and cannot execute on this
Mac.

This checkpoint is **not** disposable SQL runtime evidence, migration approval,
production migration, retention approval, Candidate, release readiness,
deployment, feature activation, or live Community evidence.

## Architecture and implementation

- `DISPOSABLE_X64_SQL_CI_PROOF_ARCHITECTURE_AMENDMENT_2026-08-02.md` defines
  the supported Microsoft-hosted Ubuntu 22.04 x64 boundary, exact pinned SQL
  and client-base images, synthetic proof sequence, evidence classification,
  and stop rules.
- `scripts/run_community_disposable_sql_proof.py` defaults to a no-action plan.
  Its hidden execution path fails closed on the host, Docker server, source
  SHA, clean worktree, Community flag, preexisting SQL/provider credentials,
  image digests, private internal network, inspected container address, SQL
  machine/build/edition, proof ordering, rollback outcomes, and exact cleanup.
- `tests/test_community_disposable_sql_proof.py` covers inert plan behavior,
  host and inside guards, immutable image identity, source binding, private
  network/container binding, exact object inventories, command secrecy,
  ordering, content-free failures, and exact cleanup.

The future supported run will apply the base platform through `PS-AUTH-001`,
apply the Community migration twice, run the unchanged two-owner verifier,
prove complete empty-domain rollback, then prove error `52490` and full state
preservation for a separately populated synthetic domain. It uses no host
mount, published SQL port, production secret, member data, or broad Docker
cleanup command.

## Verification

- 19 new harness unit/static tests: PASS.
- New harness plus existing Community runtime and migration-verifier tests:
  114 tests PASS.
- Python compilation: PASS.
- Inert plan JSON generation and parsing: PASS; no Docker/database call.
- Diff whitespace check: PASS.
- Independent Sol very-high Protected review: initial review found three P1
  false-evidence/isolation risks; all were corrected. Final review: PASS with
  no open P0/P1/P2 findings.
- SQL tag-to-digest lookup independently confirmed
  `mcr.microsoft.com/mssql/server:2022-CU26-ubuntu-22.04` as
  `sha256:ba4c8329f48fb8f02e1416be6a930ebfd71268caee78aa985f3af4315e457c89`.

## Release truth and exact next gate

No Docker or SQL package was installed. No container, database, remote CI job,
Azure resource, provider connection, environment secret, Community flag,
retention behavior, production pipeline, push, PR, merge, migration, or
deployment was created or changed.

The exact next gate is Pete's separate authorization to push this reviewed
source and run the harness once on the named disposable x64 CI agent. A passing
remote run would establish only nonproduction migration/rollback runtime
evidence. Retention, live providers, Candidate, production migration, feature
activation, and deployment remain later independent gates.
