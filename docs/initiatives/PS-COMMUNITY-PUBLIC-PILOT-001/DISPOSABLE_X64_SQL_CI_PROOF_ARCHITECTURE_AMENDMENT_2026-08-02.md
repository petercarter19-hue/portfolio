# Disposable x64 SQL CI Proof Architecture Amendment

- **Initiative:** `PS-COMMUNITY-PUBLIC-PILOT-001`
- **Path:** Protected
- **Status:** Architecture only; local repository record, not execution or release authorization
- **Scope:** Minimum future harness for supported, disposable, nonproduction Community migration proof

## Decision

The Community migration proof will use a fresh Microsoft-hosted `ubuntu-22.04` x64 CI agent and an ephemeral SQL Server 2022 CU26 container. The developer's ARM64 Mac is not accepted as equivalent evidence because SQL Server Linux containers require supported x86-64 Linux execution; no local emulator, Azure SQL Edge substitute, or persistent development database is part of this path.

The immutable database image reference is:

```text
mcr.microsoft.com/mssql/server@sha256:ba4c8329f48fb8f02e1416be6a930ebfd71268caee78aa985f3af4315e457c89
```

That digest was resolved from the human-readable tag
`mcr.microsoft.com/mssql/server:2022-CU26-ubuntu-22.04`. A later authorized
harness must record both values and fail closed unless the agent reports
`x86_64`, the image resolves to that digest, and the running SQL Server reports
the expected 2022 CU26 build, `16.0.4265.3`. Image drift requires a reviewed
amendment; a floating tag is not proof authority.

The isolated client base image is pinned as
`python:3.12-slim@sha256:cab2dbf575e971934a81e4622f5aba17aa7929719bd7e31033a3a83b97fd0464`.
It contains only the copied migration runner, SQL authorities, and
`requirements-sql.txt`; it receives no repository mount. The harness must
inspect the locally built client artifact, execute it by its immutable Docker
content ID rather than its mutable build tag, and record that executed ID
separately from the base-image digest.

## Existing implementation seams

The harness must call the repository's existing migration surfaces rather than duplicate migration logic:

- [`scripts/apply_sql_migrations.py`](../../../scripts/apply_sql_migrations.py) supplies the approved base order through `PS-AUTH-001`, selects the optional Community migration, and invokes the Community verifier.
- [`PS-COMMUNITY-PUBLIC-PILOT-001_community.sql`](../../../SQL%20FIles/Migrations/proposed/PS-COMMUNITY-PUBLIC-PILOT-001_community.sql) is the forward migration.
- [`PS-COMMUNITY-PUBLIC-PILOT-001_owner_public_verify.sql`](../../../SQL%20FIles/Verification/PS-COMMUNITY-PUBLIC-PILOT-001_owner_public_verify.sql) is the synthetic, outer-transaction verifier.
- [`PS-COMMUNITY-PUBLIC-PILOT-001_community_rollback.sql`](../../../SQL%20FIles/Migrations/proposed/PS-COMMUNITY-PUBLIC-PILOT-001_community_rollback.sql) is the guarded empty-domain rollback and populated-domain refusal authority.

No schema, migration, verifier, runtime, feature-flag, or product behavior change is authorized by this amendment.

## Isolation contract

Each proof run must:

- use one disposable CI job, a job-local Docker network, a fresh SQL Server Developer container, and fresh databases;
- keep Community feature-default-off throughout the proof;
- use synthetic identities and content only;
- generate the SQL administrator credential in job memory, mask it, never log or artifact it, and destroy it during unconditional cleanup;
- load no repository `.env`, production connection string, user data, Azure credential, or other secret;
- use no bind mount, named volume, repository mount, or retained database layer;
- publish no SQL port to the host or any remote interface; clients must connect
  by container name over the private job network and cross-check its resolved
  private address and reported SQL machine name against the exact container
  inspected by the outer harness;
- create no Azure resource and contact no Blob, Speech, Defender, production, staging, or other external provider; and
- apply bounded readiness and command timeouts so a hung server cannot leave the job running indefinitely.

Container image caching may improve transport, but a cached layer is evidence only after its content digest is verified. The database and container state must never be reused between jobs.

## Exact proof sequence

The later harness must run these steps in order and stop on the first unexpected result:

1. **Preflight.** Record the source SHA, agent image, OS, `x86_64` architecture, Docker version, image tag-to-digest mapping, resolved digest, and reported SQL build. Enforce the isolation contract and confirm the Community flag remains false.
2. **Empty-domain forward proof.** Start a fresh container and database. Use the existing runner's approved base plan through `PS-AUTH-001`, then apply the optional Community forward migration once.
3. **Idempotency proof.** Apply the identical Community forward migration a second time to the same database. It must succeed without drift, duplicate objects, or changed migration meaning.
4. **Verifier proof.** Invoke the existing Community verifier through the runner. All checks must pass, and its outer transaction must leave no synthetic Community rows behind.
5. **Empty rollback proof.** Execute the existing Community rollback against that now-empty Community domain. It must remove the Community objects and Community migration-ledger entry while preserving the base identity foundation.
6. **Populated refusal proof.** In a separate fresh database, apply the same base and Community migrations, then create the minimum valid synthetic Community membership/content through approved database interfaces. Run the unchanged rollback and require its documented nonzero refusal. Confirm the Community schema and synthetic data remain intact after refusal. Destroy this whole disposable database afterward; do not delete the row merely to force rollback success.
7. **Cleanup proof.** In an unconditional `always`/`finally` path, remove the databases, container, private network, credential material, temporary connection configuration, and any generated files. Fail the job if cleanup cannot be confirmed.

Forward-twice success, verifier success, empty rollback success, and populated rollback refusal are all required. A partial pass is a failed proof. SQL must not be weakened or rewritten to make the harness pass.

## Evidence classification

Permitted evidence is a concise machine-readable and human-readable record of:

- source SHA and exact migration/verifier file hashes;
- agent OS and architecture;
- Docker and SQL Server versions;
- SQL image tag, immutable digest, and digest verification;
- client base-image digest and the immutable content ID of the exact built
  client artifact that executed the proof;
- pass/fail and duration for each numbered proof step;
- expected versus observed rollback exit classification; and
- final cleanup confirmation.

Evidence must exclude credentials, connection strings, synthetic content bodies, user-like identifiers, raw SQL result bodies, container filesystem layers, and database files. Passing evidence means only: **the exact source was exercised successfully against a disposable, supported x64 SQL Server 2022 CU26 nonproduction runtime**. It is not Azure-provider, retention, security-certification, production, Candidate, release-readiness, deployment, or live-user evidence.

## Stop conditions

Stop without substitution if the agent is not `ubuntu-22.04` x64, the digest or SQL build differs, isolation would require a published port or mount, any non-synthetic data or external credential is detected, the Community flag is true, a proof step differs from the required result, the verifier leaves rows, the guarded rollback is bypassed, or cleanup is unconfirmed. Report rather than repair any migration or verifier defect within the proof job.

## Current implementation boundary and next gate

Pete's 2026-08-02 instruction to “Keep going” after the Mac runtime blocker
authorizes the smallest local harness and focused static/unit tests needed to
encode this contract. It does not authorize a production-pipeline edit,
container start, remote CI run, package installation, push, PR, merge, Azure
provider action, production connection or migration, retention decision or
implementation, Candidate activation, deployment, or feature-flag enablement.

The local harness work must stop before any push or remote execution. A later,
explicit authorization is required to push the harness and run it on the named
CI agent; still later authorities govern provider, retention, Candidate,
release, and deployment work.
