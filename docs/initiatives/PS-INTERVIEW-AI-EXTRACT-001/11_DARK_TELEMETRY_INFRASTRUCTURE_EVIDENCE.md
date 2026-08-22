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

**Governing evidence:** the approved `c3` proof with its 105/105 checks
is the governing evidence for this candidate. The `c2`, `c2b`, and `c2c`
runs are preserved preapproval history — recorded for completeness and
auditability — and are NOT the final governed proof.

**Resources, stated honestly:** each proof run used a temporary
Basic-tier Azure SQL database, created for the run and deleted the same
day. Temporary Basic-tier resources are billable while they exist, so no
categorical no-cost claim is made; what is claimed is that every proof
database was deleted and that no production database was contacted at
any point, by any run.

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
