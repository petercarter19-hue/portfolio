# Disposable Community SQL proof — runtime audit

**Status:** NOT RUN — blocked before any database connection
**Date:** 2026-08-02
**Repository HEAD:** `6c9c381e90efdebd5dee35d4f16f54f57bd829e4`
**Branch:** `codex/2026-08-01-community-primary-feed-sol-ultra`

## Safety boundary

This audit did not load a repository environment file, inspect a connection
secret, open a database connection, contact Azure, change a database, enable a
feature flag, or use member data. The Community public-pilot flag was not
changed.

## Local runtime result

- Docker, Podman, Colima, OrbStack, `sqlcmd`, and `mssql-cli`: not
  installed or callable.
- Docker Desktop, OrbStack, and Podman Desktop applications: not present.
- Local SQL Server process: none found.
- Listener on local TCP port 1433: none found.
- Homebrew SQL Server/container runtime formula or cask: none found.
- Python `mssql_python` client: available, version 1.11.0.

The client library alone cannot host a disposable SQL Server. Because no
isolated local SQL Server exists, the forward migration, live verifier, and
rollback behaviors cannot be executed safely on this Mac. Using the existing
`AZURE_SQL_CONNECTIONSTRING` path would violate this tranche's local-only
boundary, so no connection attempt was made.

## Confirmed runner plan

The safe plan-only command completed:

```text
/tmp/peerslate-community-review-20260801/bin/python \
  scripts/apply_sql_migrations.py \
  --migration PS-COMMUNITY-PUBLIC-PILOT-001
```

Result:

```text
PeerSlate migration plan:
- PS-COMMUNITY-PUBLIC-PILOT-001_community.sql
Plan only. No database changes were made.
```

With an explicitly local disposable connection file, the exact forward and
verification sequence is:

```text
python scripts/apply_sql_migrations.py --apply --env-file <local-disposable.env>
python scripts/apply_sql_migrations.py --apply --migration PS-COMMUNITY-PUBLIC-PILOT-001 --env-file <local-disposable.env>
python scripts/apply_sql_migrations.py --apply --migration PS-COMMUNITY-PUBLIC-PILOT-001 --env-file <local-disposable.env>
python scripts/apply_sql_migrations.py --verify --migration PS-COMMUNITY-PUBLIC-PILOT-001 --env-file <local-disposable.env>
```

The first command establishes the required foundation. The next two calls are
the intended forward/idempotency proof. The final call runs the foundation
checks and the Community two-owner synthetic verifier, whose SQL owns an outer
transaction and rolls back its synthetic rows.

The existing migration runner does not expose a rollback option. After the
commands above, execute
`SQL FIles/Migrations/proposed/PS-COMMUNITY-PUBLIC-PILOT-001_community_rollback.sql`
against the same disposable database through a local SQL client. Prove empty
rollback success in one disposable database. In a second disposable database,
publish one synthetic Community post through the approved stored procedure,
run the rollback SQL expecting error 52490, and confirm that the migration
record, objects, and synthetic post remain.

## Focused checks completed

- `scripts/apply_sql_migrations.py` Python compilation: PASS.
- `tests.test_community_public_pilot_verifier` and
  `tests.test_community_public_pilot`: 95 tests PASS.
- Independent Sol very-high review: PASS with no P0/P1/P2 findings.
- Live forward apply twice: NOT RUN.
- Live two-owner outer-transaction verifier: NOT RUN.
- Empty-domain rollback success: NOT RUN.
- Populated-domain rollback refusal: NOT RUN.

## Best next action

Provision or explicitly authorize one disposable local SQL Server runtime
(for example, a local container engine plus a pinned SQL Server Developer
image). Create fresh synthetic-only databases and an environment file whose
server is explicitly loopback/local. Then rerun the exact sequence above and
replace this blocker record with content-free PASS/FAIL evidence. Do not reuse
an Azure, shared, production, or member-data database.
