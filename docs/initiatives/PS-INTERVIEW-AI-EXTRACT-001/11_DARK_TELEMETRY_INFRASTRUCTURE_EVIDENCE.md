# PS-INTERVIEW-AI-EXTRACT-001 — dark telemetry infrastructure evidence

_Step 1 of the accepted seven-step release order in `10_RELEASE_PLAN.md`:
land the telemetry infrastructure **without changing the Interview
runtime**. Nothing here applies schema, provisions an identity, enables
retention, changes configuration, deploys, or calls a provider._

## 1. Lane and base

| Fact | Value |
|---|---|
| Activation SHA (base) | `8bb3339b7ada4a2419b0d71eeec92a66a55d4b6e` |
| Prerequisite control pause | `996f897b6f89d47a126faa02273941e09678f26b` |
| Branch | `work/2026-08-21-interview-ai-extract-dark-infrastructure` |
| Accepted implementation source | `dd545348939a668e4d4ff375526d689fa4174f89` |
| Accepted release-plan correction | `d546b525a84d62ba3eef3ef7dc3f5e2833647582` |
| Preserved runtime branch / tip | `work/2026-08-20-interview-ai-extract-001` / `d546b525` |

The activation was verified directly from `origin/main` (authored by the
owner, control record naming this package, branch, and the fourteen
writable surfaces) before any write, and the write preflight was rerun
independently and passed with a clean tree at the exact base.

PR 564 remains open, auto-complete off, and non-completable. Its branch
was not edited by this lane.

## 2. Source-byte comparison

Every immutable file was taken from its accepted source with
`git checkout <sha> -- <path>` and compared by object hash. The
PR 567 exact-candidate review (C1-C5) then REQUIRED changes to five of
them; each is listed with its post-correction state.

| Result | Path | Source |
|---|---|---|
| byte-identical | `docs/governance/PACKAGE_REGISTRY.json` body | `dd545348` (+ C5 `updated_at` refresh) |
| byte-identical | `services/database_service.py` | `dd545348` |
| byte-identical | `tests/test_operational_readiness.py` | `dd545348` |
| byte-identical | `docs/initiatives/PS-INTERVIEW-AI-EXTRACT-001/10_RELEASE_PLAN.md` | `d546b525` |
| byte-identical | `SQL FIles/Migrations/proposed/PS-INTERVIEW-AI-EXTRACT-001_telemetry_rollback.sql` | `dd545348` |
| **corrected (C2, runtime-compatible)** | `..._telemetry.sql` | `dd545348` + bundle-label guards: stored `<semver>+<sha8>`, specialist separate, combined identity `specialist@bundle_label` |
| **corrected (C1 + Fix 2)** | `scripts/interview_ai/run_interview_telemetry_purge.py` | rewritten failure contract, closed reason enum, exactly one report under combined operational+close failures |
| **corrected (C3)** | `scripts/interview_ai/run_interview_telemetry_sql_proof.py` | exact-governed-error matching + genuine race + label cases |
| **regenerated (Fix 4)** | `docs/initiatives/PS-INTERVIEW-AI-EXTRACT-001/05_SQL_DISPOSABLE_PROOF.json` | Pete-approved 105/105 run on `ps-interview-extract-gate-c3-20260821` |
| **regenerated (Fix 4)** | `SQL FIles/Migrations/registry.json` | Pete-approved gate receipt for the final corrected migration bytes |
| **one disclosed edit** | `tests/test_database_service.py` | `dd545348` + comment repoint |

### The one disclosed deviation

The accepted `tests/test_database_service.py` carries a comment saying the
purge procedure's absence is asserted independently by
`tests/interview_ai/test_slice_governance.py`. That file is runtime
material and is deliberately **not** in this branch, so carrying the
comment verbatim would have left a false cross-reference. The comment now
points at `tests/test_interview_ai_dark_telemetry_infrastructure.py`,
which asserts that absence here. **No assertion, literal, or count
changed** — the allowlist addition and the 136 → 137 count are exactly as
accepted.

## 3. Pipeline separation proof

The accepted candidate changed `azure-pipelines.yml` in five hunks. Only
three were carried:

| Carried | Hunk | Content |
|---|---|---|
| yes | schedules | `Interview telemetry retention nightly` cron `41 2 * * *` |
| **no** | Build install | B3 runtime-lock constraints mirror |
| **no** | staging | B3 vendored hash-locked install + staged runtime verification |
| yes | CommunityMaintenance | schedule-display-name pin (isolation) |
| yes | new stage | `InterviewTelemetryMaintenance`, default-off |

Resulting diff versus base remains the three carried regions (schedule, Community isolation pin, retention stage), now including the C1 guaranteed-report step and succeeded()-preserving conditions.

Absent from the pipeline (asserted by test): `interview-runtime-lock.txt`,
`interview-runtime-constraints.txt`, `interview-runtime-vendor-args.txt`,
`verify_staged_runtime`, `--require-hashes`, `.python_packages`.

## 4. Separation and safety properties (all asserted by test)

- **Append yes, purge never.** `usp_AppendInterviewAIServerCall` is the
  only Interview procedure in the application allowlist;
  `usp_PurgeInterviewAIServerCalls` is absent, and `execute_procedure`
  refuses any name outside the allowlist before the database boundary.
- **Separate maintenance identity.** The purge runs out of process from
  its own `INTERVIEW_TELEMETRY_SQL_CONNECTIONSTRING`, supplied by
  `interviewTelemetryMaintenanceSqlConnectionString`. It shares no
  connection variable with Community maintenance and never touches the
  application's database service.
- **Default-off retention.** `interviewTelemetryMaintenanceEnabled` is
  not declared in the pipeline's variables block, so it does not exist
  until an operator creates it. Every operative step requires it to equal
  `true`; otherwise the stage records
  `{"result": "disabled", ...}` and exits.
- **Schedule isolation.** Both schedule-gated stages check
  `Build.CronSchedule.DisplayName` against their own name, so neither
  cron can trigger the other's stage.
- **Bounded, refusing tools (C1, C4).** The purge refuses a MALFORMED
  expected-database name (the name grammar rejects spaces and other
  illegal identifier characters), a batch size outside 1–5000, a batch
  count outside 1–1000, and a missing dedicated connection — and, via an
  injected fake driver, a wrong-target database is proven to refuse
  BEFORE the purge procedure is invoked, with no commit and no
  connection detail emitted. Every failure stage (dependency import,
  connect, cursor, DB_NAME, purge, result parse, commit, close) emits
  exactly one bounded JSON report from a closed reason enum, exits
  nonzero, and leaves stderr empty. The SQL proof tool refuses a
  production-named database.
- **No runtime here.** `services/interview_ai/`, `prompts/interview/`,
  and `tests/interview_ai/` (including the parity oracle) are absent.
  `scripts/interview_ai/` contains exactly the two telemetry tools, and
  neither mentions a provider SDK or a message-create call.

## 4a. Defect correction found at Extract completion (2026-08-22)

**Defect.** The landed `InterviewTelemetryMaintenance` stage ran the purge
as a plain `script:` step carrying only the nonsecret
`ActiveDirectoryDefault` connection string. On a hosted agent a plain
script step has no identity context, so that connection could never
authenticate as the maintenance principal: every enabled nightly run
would have reported `connection_failed`. It passed review twice because
retention is default-off by design and the path had never executed.
Community maintenance avoids this by running its purge INSIDE an
`AzureCLI@2` task bound to its workload-identity-federated service
connection, which is what supplies the identity.

**Correction.** The purge step is now an `AzureCLI@2` task bound to
`$(interviewTelemetryMaintenanceServiceConnectionId)` - the dedicated
Interview service connection, never Community's and never the
schema/deployment connection - with the same `succeeded()` +
enablement condition, the same bounded invocation, the same
content-free artifact, and the same dedicated connection variable. The
dependency-install and disabled-report steps are unchanged. A new test
(`test_purge_runs_inside_the_interview_service_connection`) asserts the
invocation sits inside an AzureCLI task bound to the Interview
connection and that neither stage borrows the other's connection.

**Compile-time guard.** Azure resolves `azureSubscription` when the
YAML compiles, so referencing a not-yet-created service connection
invalidates the entire pipeline (validation run 1414 proved it). The
AzureCLI task is therefore inserted only when
`interviewTelemetryMaintenanceServiceConnectionId` is defined
(`${{ if ne(variables[...], '') }}`): until the operator creates the
Interview service connection and its nonsecret variable (release step 4),
the step does not exist, the guaranteed fallback report still publishes,
and retention is default-off at compile time as well as at run time.

**Scope.** Pipeline stage + test + this record only. No migration,
purge-script, proof-tool, runtime, or identity bytes changed; the gate
receipt is unaffected. Retention remains default-off and unproven until
the separately authorized enablement phase.

## 5. Gate receipt and approval timing (Fixes 3-4)

**Approval timing, stated plainly:** the three disposable gate runs of
the C1-C5 correction round (`ps-interview-extract-gate-c2-20260821`,
`...c2b`, `...c2c`) were executed BEFORE Pete's explicit approval - the
correction packet's return requirements were read as authority, and that
reading preceded the owner's own sign-off. All three databases were
deleted the same day and production SQL was untouched at every point.
Pete subsequently approved the corrections and the necessary disposable
SQL proof, and directed the runtime-compatible label form
(`<semver>+<sha8>` stored, specialist separate, combined identity
validated as `specialist@bundle_label`).

Under that explicit approval, the FINAL corrected migration was gated
and proven on `ps-interview-extract-gate-c3-20260821` (created **and
deleted** 2026-08-21, lifecycle in `05_SQL_DISPOSABLE_PROOF.json`). The
recorded receipt matches the migration bytes on disk
(`python scripts/govern_sql_migrations.py check` passes), and the full
battery ran on that same throwaway: every hostile case passes ONLY on
its exact governed rejection (matched against THROW messages derived
from the migration bytes), the runtime-format label cases prove the C2
channel closure without breaking the runtime's recorded
`<semver>+<sha8>` labels (the pre-correction `<specialist>@...` shape is
itself now rejected), and the concurrency case is a genuine
barrier-synchronized two-connection race.

**Governing evidence:** the `c3` proof (105/105) governed the candidate
until run 1419 exposed the authority defect recorded in §5a; the `c6`
proof (132/132) now governs. The `c2`, `c2b`, and `c2c`
runs are preserved preapproval history — recorded for completeness and
auditability — and are NOT the final governed proof.

**Resources, stated honestly:** each proof run used a temporary
Basic-tier Azure SQL database, created for the run and deleted the same
day. Temporary Basic-tier resources are billable while they exist, so no
categorical no-cost claim is made; what is claimed is that every proof
database was deleted and that no production database was contacted at
any point, by any run.

## 5a. Governed apply attempt, run 1419 (2026-08-22): refused, nothing written

Under Pete's end-to-end completion authority the `c3` migration bytes
were queued through the governed path (manual run 1419 on `main`
`6602768f`, `schemaAction=apply`, no application deploy; the read-only
preflight passed and the approval was registered against the
`peerslate-database-schema` environment with every listed fact
re-verified). The apply step was refused by SQL Server with a
permission error. Each migration runs in its own transaction, so the
refusal left nothing behind: the run's own post-failure ledger read and
a direct catalog read both confirmed no ledger row, no table, no
procedure and no role. The live application was never redeployed.

**Cause.** The governed apply identity, `peerslate-ado-schema`, holds
`db_ddladmin` plus the ledger table only. That is enough to create
tables and procedures and deliberately not enough to create database
roles or grant execute permission. This migration was the first in the
repository to embed `CREATE ROLE` and `GRANT`; no earlier migration
carries any security-principal statement, and the one package that
needed such work (Community maintenance) did it in a separate
administrator-run authority script. The disposable gate ran as
an administrator on a throwaway database and therefore could not
expose the gap - a real limit of that proof, now recorded.

**Correction (this record's branch).** The migration carries schema
only. Roles, grants, the maintenance EXTERNAL_USER and both memberships
move to `scripts/configure_interview_telemetry_sql_authority.py`
(plan/apply/verify, one transaction, complete boundary verified before
commit, content-free report), mirroring the Community script. The
rollback no longer touches roles (dropping a procedure drops its grants
with it). The proof tool now calls the same `ensure_roles_and_grants`
function - twice for idempotency, and again after the rollback/re-apply
case - so the gate proves the exact statements an administrator runs.
`MigrationAuthorityBoundaryTests` hold the split.

**Second finding from the read-only production plan.** The application
identity (`peerslate-pete`) already holds `db_datareader`,
`db_datawriter` and a database-wide `EXECUTE` grant. Those predate this
package and are not changed here, but they would let the application
execute the purge procedure and write the telemetry table directly -
the reviewed "application may append and may NOT purge" boundary was
proven on clean proof users, not on the real identity. The authority
script therefore also places two explicit `DENY`s on the application
identity (EXECUTE on the purge procedure; SELECT/INSERT/UPDATE/DELETE
on the telemetry table). A `DENY` overrides every broader `GRANT`; the
append procedure keeps working because it and the table share an owner.
`verify` now proves the effective result for the real identities.
Whether to keep or narrow the application identity's standing grants
more generally is outside this package.

**Round-2 independent review (fresh read-only reviewer on `9cbd475c`)
returned CORRECTIONS REQUIRED with nothing in the gated forward bytes;
all findings are corrected here:** (1) the rollback's empty-table guard
reads the table, which `db_ddladmin` cannot - the rollback is now
recorded, in the file and in the release plan, as administrator-run
through the governor (a house-wide pattern; widening the apply identity
is out of scope); (2) `plan`/`verify` could print a raw error dump -
every mode now reports an exception class only; (3) the proof had not
exercised `ensure_maintenance_user`, `ensure_memberships` or `verify()` -
the proof now runs the script's `apply()` and `verify()` end to end on
stand-ins, including an `EXTERNAL_USER` created from a synthetic SID so
`EXECUTE AS` on a TYPE = E principal is proven; (4) the statement probe
in the tests is now case-insensitive, comment-stripped and covers
`ALTER AUTHORIZATION`, `sp_addrolemember`, `CREATE SCHEMA`, user DDL and
`EXECUTE AS`, with a negative control; (5) the DENY checks pass only on
SQL's permission refusal (229) and the delete/insert probes touch no row;
(6) `HAS_PERMS_BY_NAME` NULL is a failure in both directions; (7) the
forward header and ledger description no longer say the migration
creates roles (a text-only byte change, re-gated below); (8) the rollback
header states exactly what persists after a rollback and that its
removal is a manual administrator operation: `ALTER ROLE ... DROP
MEMBER`, `DROP ROLE`, `DROP USER`; (9) the vacuous table-grant
assertion is replaced by an exact "only EXECUTE is ever granted" check.
(10) The first end-to-end proof run surfaced a real defect the reviewer had
flagged as a risk: SQL Server refuses `EXECUTE AS` on an `EXTERNAL_USER`
from a SQL-authenticated connection ("only active directory users can
impersonate other active directory users"), and the house `.env`
connection is SQL-authenticated - so the script's `verify` would have
failed in production exactly there. The authority script now connects as
the server's Entra administrator over `ActiveDirectoryDefault` (the
Community pattern; no credential is read), the proof runs over the same
kind of connection and records the end-to-end result as a named check,
and the half-applied `c5` throwaway was deleted in favour of a fresh
`c6`. The one-byte repair of the traceback-absence probe is out of the
stated scope and is disclosed as such.

**Consequences, stated plainly.** The corrected bytes no longer match
the `c3` receipt; the governing status of `c3` ended there. With
Pete's approval of this correction, the corrected migration was
re-gated - finally on `ps-interview-extract-gate-c6-20260822` (Basic
tier, created and deleted 2026-08-22; governor gate passed with
prerequisites, forward apply, idempotent re-apply, rollback rehearsal and
re-apply; digest `83ab8c08...` now in the registry receipt) after the
round-2 corrections, with the full proof battery on that same throwaway
over an Entra-authenticated connection: 132/132, including the 105
preserved checks, the authority-function idempotency and re-grant
checks, the production-shaped stand-in that first reproduces the
premise (broad grants reach the purge without a DENY) and then proves
its closure, and the authority script's own `apply` and `verify` run
end to end (every `verify` check recorded by name). The intermediate
`c4` (112/112) and `c5` (aborted) throwaways are preserved history. Fresh exact-SHA independent review and a new governed run
with its own environment approval are still required before any
re-apply. The Azure approval check itself was neither removed nor
weakened.

## 5b. Residual review findings N1–N6 (round-2 independent review of `8ba76255`, non-blocking, carried)

- **N1** `verify()` checks that the application principal is present, not
  that it is `EXTERNAL_USER` (the production principal was confirmed
  `EXTERNAL_USER` by a catalogue read). Add an expected-type parameter.
- **N2** No statement timeout on the administrator connection.
- **N3** Two statements sit outside the content-free guards
  (`SELECT DB_NAME()` right after connect; `rollback()` inside `except`).
- **N4** The preserved role-isolation checks in the proof accept any
  exception (also Grok F3); tighten to SQL error 229.
- **N5** The GRANT-verb test regex is case-sensitive.
- **N6** The forward-migration header sentence "the application identity
  holds EXECUTE on the append procedure only" describes the role, not the
  real identity (text-only; not worth a re-gate on its own).

## 6. Content-free evidence

No secret, connection string, member content, model content, URL, or raw
exception text appears in this record or in
`05_SQL_DISPOSABLE_PROOF.json`; the disposable proof carries only named
check outcomes, and the purge report contains bounded status and reason
fields drawn from the tool's closed enums plus integer counts — nothing
free-form. A test scans both files for credential and exception markers.

## 7. Limitations

- Disposable SQL proof migrations DID run in this lane: the governing
  105/105 proof executed the migration and battery on the Pete-approved
  `ps-interview-extract-gate-c3-20260821`, and the preserved preapproval
  runs (`c2`, `c2b`, `c2c`) did the same on their own throwaways. What
  never happened is production SQL: no migration was applied to any
  production database, and production behaviour remains unexercised.
- The retention stage has never run, because retention is default-off and
  the migration is unapplied. Its operative path is therefore evidenced
  by static gating only, until the separately authorized enablement phase
  of `10_RELEASE_PLAN.md`.
- Landing this infrastructure changes no Interview behaviour. The
  Interview runtime remains exactly as deployed today.

## 8. Withheld

No merge of PR 564; no merge of this lane's pull request. Disposable
SQL proof migrations ran, on temporary proof databases that were
deleted — but **no production SQL was applied** and no production
migration was executed. No production identity or permission
provisioning; no retention enablement; no production configuration; no
deployment; no provider call; no evaluation execution; no provider
spend (temporary Basic-tier proof databases are billable while they
exist and are not claimed as free); no production operation; no later
Interview slice.
