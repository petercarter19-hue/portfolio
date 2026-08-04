# Disposable SQL proof — run 344 root cause and minimum correction

- **Initiative:** `PS-COMMUNITY-PUBLIC-PILOT-001`
- **Path:** Protected
- **Writer:** Claude (sole Community writer after the 2026-08-02 Codex-to-Claude
  transfer; the Codex Mac worktree and the PC `pscf` worktree remain frozen)
- **Status:** Root cause identified with static evidence; correction implemented
  and focused-tested; a third disposable run requires Pete's explicit gate

## Diagnosed failure

Run `344` (source `2234597b2024ee1f1eb5e706cf8b94aff345003f`) sealed
`inside_preflight_unexpected`: the isolated client container raised a
non-allowlisted exception inside its `preflight` stage. Neither run's evidence
was altered by this diagnosis; both checksum sets were re-verified byte-for-byte
before analysis.

## Root cause

The pinned client base image `python:3.12-slim` does not contain the system
shared libraries that the `mssql-python==1.11.0` driver requires at connect
time on Debian-family Linux. The wheel bundles
`libs/linux/debian_ubuntu/x86_64/lib/libmsodbcsql-18.6.so.2.1`, whose ELF
`DT_NEEDED` entries include `libkrb5.so.3` and `libgssapi_krb5.so.2`, and the
bundled `libodbcinst.so.2` additionally requires `libltdl.so.7`. None of the
three is present in the slim base image. Microsoft's mssql-python
documentation lists the same Debian/Ubuntu prerequisites:
`libltdl7 libkrb5-3 libgssapi-krb5-2`.

Failure localization, consistent with every allowlisted code that did **not**
fire:

1. `from mssql_python import connect` succeeds, because the Python-facing
   `ddbc_bindings` extension needs only `libstdc++`/`libgcc`, which the slim
   image has. This is why the allowlisted `migration_runner_import_failed`
   code did not appear: `scripts/apply_sql_migrations.py` imports
   `mssql_python` at module top and imported cleanly.
2. Job-local DNS resolution passed, or the allowlisted
   `sql_job_local_name_resolution_failed` / `sql_job_local_address_mismatch`
   codes would have appeared.
3. The first real driver load happens at `_connect(master)` inside
   `_validate_job_local_sql_target` — the child's `preflight` step. The
   driver's dynamic load fails on the missing Kerberos/ltdl libraries and
   raises a generic driver exception, which the content-free classifier
   correctly binds to `preflight_unexpected`.

Supporting static verification performed without any container or SQL action:

- ELF `DT_NEEDED` inspection of the exact
  `mssql_python-1.11.0-cp312-cp312-manylinux_2_28_x86_64.whl` payload
  (`ddbc_bindings.cp312-x86_64.so`, the Debian/Ubuntu
  `libmsodbcsql-18.6.so.2.1`, `libodbcinst.so.2`, and
  `mssql_py_core.cpython-312-x86_64-linux-gnu.so`).
- Local execution of `_build_context()` confirming the client build context
  contains the complete `SQL FIles` tree, `requirements-sql.txt`, and both
  scripts, ruling out the only other non-allowlisted `preflight` path
  (a missing-file error while hashing the three Community SQL files).
- Driver API verification that `connect(..., timeout=...)` and
  `Connection.setautocommit(...)` exist in 1.11.0 as used by the harness.

Run `339`'s earlier `external_command_failed` belongs to the pre-diagnostic
harness generation and stays immutable; it cannot and need not be reclassified.

## Minimum correction

One bounded change in `scripts/run_community_disposable_sql_proof.py`
`_build_context()`: the generated client Dockerfile now installs the three
documented driver runtime packages before `pip install`:

```dockerfile
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgssapi-krb5-2 libkrb5-3 libltdl7 \
    && rm -rf /var/lib/apt/lists/*
```

Boundary notes:

- Build-time package installation from the Debian archive is the same class of
  network fetch the existing `pip install` layer already performs; the client
  base image and SQL image remain digest-pinned, and no port, volume, service
  connection, credential, or production surface is introduced.
- The three packages are runtime shared libraries only; they are not pinned to
  exact Debian point versions because the archive retires point releases, and
  a stale pin would make the proof unrunnable for a reason unrelated to its
  contract.
- No SQL, migration, verifier, evidence-schema, allowlist, pipeline-topology,
  or cleanup behavior changed.

Focused coverage added in `tests/test_community_disposable_sql_proof.py`
(`test_build_context_installs_documented_driver_runtime_libraries`): exactly
one install line, all three packages present, `--no-install-recommends`, apt
list cleanup, and system-library installation ordered before `pip install`.

## RESOLVED, 2026-08-03 — the connection string dropped the credentials

**Root cause, proven locally rather than inferred:** the proof built an
ADO.NET-style connection string, but `mssql-python` speaks ODBC. It normalizes
a fixed keyword set and *silently discards* everything outside it. Parsing the
exact string with `mssql-python==1.11.0` shows:

| Keyword used | Normalizes to |
|---|---|
| `Initial Catalog` | `None` — discarded |
| `User ID` | `None` — discarded |
| `Password` | `None` — discarded |
| `Connection Timeout` | `None` — discarded |

The string that actually reached the driver therefore carried only `Server`,
`Encrypt`, and `TrustServerCertificate`. Every login was attempted **with no
username, no password, and no database**, which is exactly why the failure was
identical whether encrypted or not, and why it survived a Kerberos-library fix
and an OpenSSL security-level fix. Switching to `Database=`, `UID=`, and
`PWD=` restores all six parameters; the login timeout now travels as the
`timeout` argument to `connect()`.

Verified by parsing both spellings locally with the real driver:

- old → `['Encrypt', 'Server', 'TrustServerCertificate']`
- new → `['Database', 'Encrypt', 'PWD', 'Server', 'TrustServerCertificate', 'UID']`

**Confirmed by run 392**, the first run on the corrected string: the sealed
code moved from `inside_sql_connect_failed` to
`inside_empty_forward_unexpected`. Preflight and database setup now pass, so
the client authenticates, reads server identity, and creates the two proof
databases. Cleanup remained confirmed on every run.

## PROOF PASSED — run 422, 2026-08-03

Azure DevOps run `422` on definition `2`, source SHA
`fead3757aa1c8138cbeba238e1b3ebd21f40e502`, branch
`codex/2026-08-01-community-primary-feed-sol-ultra`, manual reason:
**succeeded**. Sealed record reports `none_proof_passed`; every task in the
job succeeded; "Exact job-owned resource cleanup is confirmed." Retention
lease `614` protects the run and its evidence until 2036-07-31.

All six proof steps now pass on a disposable SQL Server 2022 container:
preflight, empty forward, forward idempotency, two-owner verifier, empty
rollback, and populated rollback refusal — plus unconditional cleanup.

**This satisfies the package's before-merge gate 1**: migration and rollback
validation with a two-owner verifier that prints no member content. It does
not by itself satisfy any other gate.

### Defects found — three in the product, two in the proof

Product defects that would have hit production:

1. **`dbo.app_users` created by no migration** (PS-PLAT-000, above).
2. **Savepoint name over the 32-character limit** (error 103, above).

Proof defects that made a correct product look broken:

3. **ADO.NET connection-string keywords** silently dropped the credentials.
4. **The refusal assertion matched on the number `52490`**, which this driver
   never surfaces, so a *correct* refusal was reported as an unexpected
   failure. The rollback interlock had been working the whole time.

Self-inflicted, recorded for honesty:

5. **A UTF-8 BOM** introduced by PowerShell `Set-Content -Encoding utf8`.

### Original defect analysis

**1. `dbo.app_users` was never created by any migration (PS-PLAT-000).**
Six migrations declare foreign keys against it, but the table was created by
hand in production before the migration system existed. A database could not
be built from this repository at all — a genuine disaster-recovery gap that no
test caught because production already had the table. Added as PS-PLAT-000; a
no-op plus one ledger row on production.

**2. A savepoint name exceeded SQL Server's 32-character limit.**
`SAVE TRANSACTION CommunityMediaCompletionCompensation` is 36 characters.
Savepoint names are capped at 32, unlike ordinary identifiers at 128, so the
server raised error 103 and the entire Community migration failed. This would
have failed the production migration identically. Shortened to
`CommunityMediaCompleteComp`, with a guardrail asserting every savepoint fits
and that no rollback names an undeclared savepoint.

**3. Self-inflicted, recorded for honesty:** the savepoint fix was applied
with PowerShell `Set-Content -Encoding utf8`, which writes a UTF-8 BOM. The
BOM reaches the server verbatim and is rejected as incorrect syntax, so run
413's error 102 was mine, not a third defect. Stripped, verified the file then
differed from its pre-fix state by exactly one line, and added a guardrail
asserting no SQL file carries a BOM.

### Where the proof now stands

**Run 415: five of six proof steps pass.**

| Step | State |
|---|---|
| preflight | passes |
| database_setup | passes |
| empty_forward | **passes** — all nine foundation migrations and the Community migration apply to an empty database |
| forward_idempotency | **passes** — re-applying is safe |
| two_owner_verifier | **passes** — and leaves no rows behind |
| empty_rollback | **passes** — rollback restores a clean database |
| populated_rollback_refusal | **fails** — `inside_populated_rollback_refusal_unexpected` |

The remaining step publishes a synthetic post and asserts that rollback
*refuses* to run while real content exists. That is the safety interlock which
stops an operator destroying member data, so it is the right last thing to
prove and worth getting exactly right.

### Superseded position (before the defects above were found)

| Stage | State |
|---|---|
| preflight | passes |
| database_setup | passes |
| empty_forward | **fails** — `inside_empty_forward_unexpected` |
| later stages | not reached |

`empty_forward` applies the foundation migrations and then the Community
migration to an empty database. This is a genuine SQL-execution failure and
the first real result the proof has produced — the harness is finally doing
the job it was built for. Diagnosing it needs the same treatment applied to
preflight: split `empty_forward` into distinct content-free codes so a failing
foundation migration, a failing Community migration, and a runner batching
problem are told apart. Note the migrations target Azure SQL Database while
the proof runs SQL Server 2022 in a container, so an Azure-only construct is a
plausible candidate.

### Two lessons, both about diagnosability rather than SQL

1. **A confident diagnosis with no failing-path evidence is a guess.** The
   Kerberos root cause below was plausible, documented, and wrong. It survived
   because the evidence could not contradict it.
2. **Content-free must still be diagnosable.** Three runs produced a code
   nobody could read, and one bucket covered five unrelated conditions. The
   fix that actually mattered was making failures distinguishable; the real
   bug then fell out in a single local test with no CI run at all.

## SUPERSEDED — the diagnosis below was not confirmed

**The missing-Kerberos-libraries diagnosis was wrong, or at least
insufficient.** The `apt-get install libgssapi-krb5-2 libkrb5-3 libltdl7`
correction in `0cc6c53` was exercised by run 351 and the proof still failed
with the same `inside_preflight_unexpected`. Run 382, with the sealed code
echoed to the build log, confirmed the identical code again.

What was actually established, by narrowing the preflight bucket into distinct
content-free codes and rerunning:

- Run 383 sealed **`inside_sql_connect_failed`**.
- Therefore the three reviewed SQL files are present and readable inside the
  client image (`sql_source_files_unreadable` did not fire).
- Job-local DNS resolves `community-sql` to exactly the expected container
  address (`sql_job_local_name_resolution_failed` and
  `sql_job_local_address_mismatch` did not fire).
- `apply_sql_migrations.py` imports cleanly, so the `mssql_python` Python
  extension loads (`migration_runner_import_failed` did not fire).
- The failure is the driver connection itself.

Remaining candidates, now genuinely narrow: a native library the bundled
`msodbcsql18` still cannot load, TLS negotiation between OpenSSL 3 on the
Debian-based `python:3.12-slim` client and SQL Server 2022's self-signed
certificate, `sa` authentication, or the SQL container not yet accepting
network connections even though `sqlcmd` on its own loopback succeeded.

A `sql_tcp_unreachable` probe (commit `0c14d5c`, pushed, **not yet run**)
opens and closes a plain socket to the job-local SQL port before the driver
runs. Its result splits those candidates decisively: `sql_tcp_unreachable`
means a job network problem; a surviving `sql_connect_failed` means the
driver, TLS, or authentication. Queue one run on that exact SHA to settle it.

Two process points worth keeping:

1. The evidence was unreadable to the operator. The sealed code lived only in
   a PipelineArtifact, and downloading one requires a personal access token.
   Three runs produced a value nobody could read. The seal step now echoes the
   finite allowlisted code to the build log.
2. A single `preflight_unexpected` bucket spanning three unrelated conditions
   invited exactly the confident-but-unverified diagnosis recorded below.
   Granular codes cost one commit and would have prevented two wasted runs.

## Residual uncertainty

Without executing a container, the missing-library cause is established by
direct ELF dependency evidence and vendor documentation rather than by a live
reproduction. If a third authorized run still fails, the diagnostic
architecture now guarantees a precise allowlisted code for every later stage,
so the next failure (if any) will localize itself.

## Gate

No third disposable run is queued. Queueing one manual, source-bound run of
definition `2` on the reviewed corrected SHA requires Pete's explicit
authorization, per `DISPOSABLE_X64_SQL_CI_PROOF_ARCHITECTURE_AMENDMENT_2026-08-02.md`.
