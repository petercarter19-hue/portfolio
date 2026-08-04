# The governed database migration path

**Status:** built and proven against a throwaway database. Production runs 497
and 501 proved its fail-closed parser and identity boundaries; neither applied
migration SQL. The Azure environment, secret variable, and contained pipeline
identity are now configured. A successful production apply and committed live
state record remain outstanding.

PeerSlate's application code has a reviewed, gated, auditable route to
production: pull request, CI, Azure pipeline, release record. Until now its
database schema had none.

Three migrations reached `peerslate-database` in the week of 2026-08-03 —
`PS-OPPSLATE-001` twice, plus a foundation repair — applied by an agent that
connected directly to the production database with a credential it read out of
App Service settings and executed SQL by hand. Each apply was careful: a
throwaway-database gate first, a PITR restore point recorded, a member-data
fingerprint before and after, isolation verification after. But that was
diligence substituting for a control, and it produced exactly the failures you
would predict:

- Nothing in the repository could say which revision production carried.
  `PS-OPPSLATE-001`'s header stated confidently that production was on the OS-1
  revision for several hours after production moved to OS-2.
- `docs/AI_WORKFLOW.md` and `AGENTS.md` both state that Azure DevOps is the only
  production deployment path, so every one of those applies contradicted the
  repository's own governance.
- The safety of each apply depended on one agent choosing to do the right
  things, in the right order, from a prose brief.

This document describes the replacement. It lives in PS-OPS-001 because schema,
migration, and canonical-data changes are already named there as Protected —
this is the missing mechanism for a control the package always required, not a
new initiative.

## The moving parts

| Thing | What it is |
|---|---|
| `SQL FIles/Migrations/registry.json` | The ordered inventory of all 23 migrations. Identity, files, prerequisites, and a gate proof. Records **no** claim about what any database carries. |
| `scripts/migration_registry.py` | Pure logic: ordering, digests, gate verification, plan resolution, state rendering. No connection, no credential, fully covered by tests that run on every build. |
| `scripts/govern_sql_migrations.py` | The operational entry point: `check`, `preflight`, `report`, `gate`, `apply`, `rollback`. |
| `azure-pipelines.yml` → `ProductionOperation` | The one sequential reservation shared by production application and schema operations; it is the only supported way to move production schema. |
| `docs/governance/PRODUCTION_SCHEMA_STATE.md` | The repository's record of what production carries. Generated from a live ledger read; never hand-written. |
| `scripts/apply_sql_migrations.py` | Unchanged and still used for foundation verification. A test now pins its `MIGRATION_FILENAMES` to the registry so the two cannot disagree. |

## The trigger

**Schema never moves because a pull request merged.** Merging a migration file
changes nothing in any database, and that is deliberate — it was a real
production incident on 2026-08-04 when merging `PS-PLAT-000` was reported as
"the database can now be rebuilt from the repository" while the ledger row did
not exist.

Moving schema requires all five of:

1. **A person queues the pipeline on `main`** and selects a `schemaAction` other
   than `none`. The parameter defaults to `none`, so every ordinary run —
   including every merge — skips the stage entirely.
2. **The `Build` stage passes.** The stage `dependsOn: Build`, so the full test
   suite, dependency audit, secret scan, and explicit registry/digest check all
   gate it.
3. **The hosted read-only preflight passes before approval.** It connects only
   to identify the target and read `dbo.schema_migrations`. Apply is refused
   when the named ID is already ledgered, the gated bytes changed, or the live
   plan is not exactly the one migration the operator named.
4. **An approver releases the `peerslate-database-schema` environment.** This is
   who can pull the trigger: whoever is on that environment's approval check.
5. **The mutation job revalidates the registry and proof** after approval and
   before executing any migration SQL.

The shared `ProductionOperation` stage is `lockBehavior: sequential`, not
`runLatest`. It serializes web deploys and schema actions across runs, and the
request preflight refuses any run that asks for both. A schema run therefore
cannot overlap a production deployment or be discarded in favour of one.

## Safety properties

### 1. Idempotent and ordered

Order comes from `registry.json`, where a prerequisite must appear above
anything that requires it — a test enforces it. What is *pending* comes from
reading `dbo.schema_migrations` on the target, never from a hardcoded list. That
is the specific defect being fixed: `MIGRATION_FILENAMES` named eight files
while eleven more were applied out of band, so the repository's idea of the
world and the database's had no relationship.

Re-running is a genuine no-op: the second run reads the ledger, finds nothing
pending, and applies nothing. Every migration is *also* individually idempotent,
and the gate proves that rather than trusting the header — it applies the
migration twice and fails unless the object inventory and ledger row count are
identical after the second run.

### 2. Fail closed, and fail loudly

The applier resolves a complete plan before executing anything and refuses the
whole plan if any part of it is unsafe. It will not apply a partial plan.

It refuses when: a migration is not registered; a named migration has no gate
proof; a gate proof no longer matches the file; a prerequisite is neither
applied nor in the plan; the connection is attached to a database other than
`--expect-database`; or the operator's `--expect` list differs from the plan the
ledger produces.

If a migration fails mid-plan, the run stops, exits non-zero, names the
migration that failed, and reports the ledger exactly as it stands — which
migrations committed, which were not attempted, and what the database now
carries. Each migration runs inside its own transaction, so a failed migration
leaves nothing behind and the next run resumes from the ledger.

**A no-op is visibly distinguishable from an apply.** The pipeline already
learned this the hard way: build 438 was a manual `main` run that skipped
`ProductionRelease`, reported `succeeded`, and was reasonably mistaken for a
release. `ProductionReleaseSkipped` exists because of that. The same rule
applies here — an `apply` run that finds nothing pending emits a warning naming
the database and downgrades the run to `succeededWithIssues`. If you queued a
run expecting schema to move and it did not, the run says so.

### 3. Prove before applying

**A migration cannot be applied unless its registry entry carries a gate proof
whose digest matches the T-SQL on disk.** This is a mechanical refusal, not a
convention.

`govern_sql_migrations.py gate` runs the migration against a throwaway database
and, only if all of the following pass, emits the proof:

1. apply the transitive prerequisite chain;
2. apply the migration — it must succeed and register its own ledger row;
3. apply it **again** — the object inventory and ledger must be unchanged;
4. run its verification script, if one exists — it must return `verified = 1`;
5. run its rollback — the ledger row and the created objects must disappear;
6. apply it once more — the ledger row must come back.

The proof records the digest, timestamp, gate database and server, the
prerequisite chain, the objects created, the verification result, and the
operator. It goes into `registry.json`, so it arrives in a pull request as a
reviewable diff rather than as a claim in a chat log.

The digest covers the **executable body** — everything after the leading block
comment, with line endings normalized. That choice matters both ways: a stale
header can be corrected without forcing a re-gate (exactly the fix
`PS-OPPSLATE-001` needed), while changing one character of T-SQL invalidates the
proof and the applier refuses until the migration is gated again.

There is a second, independent check at apply time. After each migration
succeeds, the applier confirms that every object the gate recorded actually
exists on the target. A proof that does not describe the migration it claims to
describe fails there.

> This digest is **not** the same number as the `executable SHA-256` quoted in
> the 2026-08-03 and 2026-08-04 `PS-OPPSLATE-001` apply records. Those used a
> different byte range. Do not compare them.

### 4. Credentials from pipeline secrets and the approved Azure identity only

The connection string comes from a secret pipeline variable
`schemaConnectionString`, defined in Azure pipeline metadata — the same pattern
the Candidate queue values already use, and for the same reason: a value
declared in YAML would shadow the reviewed one. It reaches the script as process
environment data, never as Bash source, and is never echoed.

The script never writes a connection string to disk, and scrubs the configured
value, any `Pwd=`/`Password=`/`Uid=` fragment, and the password itself out of
every message and evidence file before either is written.

The production connection uses Microsoft Entra authentication rather than a
database password. Each connected action (`report`, `apply`, and `rollback`)
therefore runs inside `AzureCLI@2` with the repository's existing
`azureServiceConnectionId`. That task supplies the short-lived Azure CLI token
that `DefaultAzureCredential` needs on a Microsoft-hosted agent. The offline
registry and gate-proof check remains a plain shell task and receives neither
the connection string nor an Azure login. Run 501 demonstrated the fail-closed
case: before these task boundaries were corrected, the hosted agent reported
that every supported Azure credential was unavailable and no migration SQL was
applied.

Azure RBAC and Azure SQL data-plane authorization are separate. The service
connection is mapped in `peerslate-database` to the contained external user
`peerslate-ado-schema`. That user is a member of `db_ddladmin`, can view
database definitions, can read and maintain only `dbo.schema_migrations`, and
can execute only `dbo.usp_AppendAuditEvent` beyond the permissions supplied by
the fixed role. It is not a member of `db_datareader`, `db_datawriter`, or
`db_owner`. A migration that genuinely needs a data backfill must receive and
document the additional narrow permission it needs; the runner does not gain
standing read/write access to member tables merely for convenience.

`--expect-database` is required for every action. The script reads `DB_NAME()`
on the open connection and refuses to continue unless it matches. A stale or
mistyped secret therefore fails closed instead of applying somewhere
unintended.

### 5. The repository records what production carries

`docs/governance/PRODUCTION_SCHEMA_STATE.md` is **generated**, not written.
Every action — including `report`, which changes nothing — reads the live ledger
and renders the file deterministically, with a "do not edit by hand" banner and
a machine-readable JSON block. Because rendering is deterministic, the file can
be regenerated and byte-compared rather than reviewed by eye.

Before an apply, the run compares the committed record against the ledger as it
stood when the run started, and warns if they disagree. That is the drift
detector: the record can lag by exactly one apply — the commit has not happened
yet — but it cannot lag silently by two, because the next run says so.

The record also surfaces anything in the ledger the repository cannot explain.
If a migration id appears in `dbo.schema_migrations` that is not in the
registry, it is listed under "Ledger rows this repository cannot explain" —
which is how out-of-band applies become visible instead of invisible.

**The file does not exist yet.** The path's first `report` run creates it. That
is deliberate: it is more honest for the repository to make no claim than to
ship a hand-written guess, and it means the record is derived from day one. See
"Telling what production carries" below for what to do until then.

## Applying a migration

1. **Gate it.** Create a throwaway database and prove the migration against it:

   ```bash
   MSYS_NO_PATHCONV=1 az sql db create --resource-group peerslate \
     --server peerslate --name ps-<slug>-gate-<yyyymmdd> \
     --service-objective Basic --collation SQL_Latin1_General_CP1_CI_AS

   python scripts/govern_sql_migrations.py \
     --database ps-<slug>-gate-<yyyymmdd> \
     gate PS-YOUR-MIGRATION \
     --expect-database ps-<slug>-gate-<yyyymmdd> \
     --operator "<who you are>" --update-registry

   MSYS_NO_PATHCONV=1 az sql db delete --resource-group peerslate \
     --server peerslate --name ps-<slug>-gate-<yyyymmdd> --yes
   ```

   The gate refuses to run against `peerslate-database` or `peerslate-staging`.
   Delete the throwaway database when you are done; it is not free and it is not
   evidence.

2. **Open a pull request** containing the migration and the gate proof. The
   proof is the reviewable artifact: a reviewer can see which bytes were proven,
   where, when, and by whom.

3. **Merge it.** Nothing happens to any database. This is correct.

4. **Queue the pipeline on `main`** with `schemaAction: apply` and
   `schemaMigrationId` set to the one migration id. The ID is required. The
   read-only preflight and applier both compare it with the live-ledger plan
   and refuse if they differ.

5. **Approve the `peerslate-database-schema` environment.**

6. **Read the stage output.** It prints the plan, what it applied, and the
   resulting ledger. Download the `SchemaMigrationEvidence` artifact.

7. **Commit the regenerated `PRODUCTION_SCHEMA_STATE.md`** from that artifact.
   Until you do, the repository's record lags by one apply and the next schema
   run will warn about it.

Application code and schema remain separate actions inside one shared
production reservation. A deliberate schema-only run does not deploy the
application and is not downgraded by `ProductionReleaseSkipped`; that warning
stage is reserved for a manual run that requested neither web deployment nor
schema work. Read the operation and stage results, not the run icon alone.

## Rolling a migration back

Rollback is destructive on member data and is deliberately awkward.

- Only the **most recently applied** registered migration may be rolled back.
  Anything else would remove objects a later migration stands on; the applier
  refuses with a readable reason before the rollback scripts refuse with a
  `THROW`.
- The operator must type the migration id **twice**, into two separate queue
  parameters (`schemaMigrationId` and `schemaRollbackConfirm`). They must match
  exactly.
- The environment approval still applies. Whoever approves `apply` approves
  `rollback`.
- The rollback scripts do the real protection. They refuse when member data is
  present, when a later migration is recorded, and — for the newer ones — when a
  procedure definition has drifted from its recorded hash. A refusal is normally
  the correct outcome.

Evidence: the run prints and publishes the ledger before and after, the exact
list of objects removed, and the regenerated state record. A rollback that
reports success but leaves its ledger row in place is treated as an unknown
state and fails.

**Rollback is not a substitute for a restore.** If member data is present, the
rollback will refuse, and it should — recovering from that is a PITR restore
decision, not a migration decision.

## Telling what production carries

Read `docs/governance/PRODUCTION_SCHEMA_STATE.md`.

**Until the first governed run generates it,** the repository does not know, and
you should run `report` to find out:

```bash
# Requires the production connection string in the environment.
python scripts/govern_sql_migrations.py report \
  --expect-database peerslate-database --write-state
```

or queue the pipeline with `schemaAction: report`, which is read-only.

Do not trust migration headers, completion reports, or package READMEs on this
question. Several are stale right now — including the header of
`PS-OPPSLATE-001` on `main`, which still says production carries the OS-1
revision when it carries OS-2. That correction is in flight on
`work/2026-08-04-opportunity-slate-os4`; this path deliberately does not edit
that file, both to avoid a conflict with an active lane and because the point of
the design is that prose is not the record.

## What `proposed/` means now

**Nothing. It is a frozen legacy directory, not a status.**

The split was the root of the mess: everything real — Capture, Moment, Journal,
Workshop, Opportunity Slate — sat in `proposed/` and was applied out of band,
while `MIGRATION_FILENAMES` listed only PS-PLAT and PS-AUTH. Two of the
migrations in `proposed/` have been in production for weeks. The directory name
never meant what it said.

The new rules:

- **The registry is the authority, not the directory.** All 23 migrations are
  registered, wherever they physically live. A test fails if any `.sql` file in
  either directory is unregistered, so a new migration cannot quietly appear
  outside the path again.
- **A migration "graduates" by acquiring a gate proof**, not by moving. Eleven
  are gated today; nine are not. Files are not being moved in this change: the
  paths are load-bearing in several test suites and at least two active lanes
  own files in that directory. Moving them is a mechanical follow-up, not part of
  this control.
- **New migrations go in `SQL FIles/Migrations/`.** Nothing new should be added
  to `proposed/`.

### Nothing was bulk-registered as applied

This is the most important line in the document. **Being in the registry says
nothing about being applied anywhere.** The registry has no field for it, and a
test enforces that it never grows one.

Some of these migrations are genuinely in production and most are not, and
guessing would have been the worst possible outcome. So the path does not guess:
it reads `dbo.schema_migrations`. On production, the pending set will be
whatever the ledger says is missing, and any of those that are ungated are held
back rather than applied.

Eleven migrations carry gate proofs from this work — `PS-PLAT-000` through
`PS-PLAT-007`, `PS-AUTH-001`, `PS-WORKSHOP-001`, `PS-OPPSLATE-001` — the chain
that reaches the most recent production migration. The other twelve are drafts as
far as this path is concerned, including the three Community migrations that
merged into `main` while this work was in flight. Several of *those* are also in
production; that is fine and creates no risk, because a migration already in the
ledger is never pending, so its draft status never blocks anything. It only means
the path will not apply them anywhere new until someone gates them.

## What this path does not protect against

Stated plainly, because a control that oversells itself is worse than none.

- **A hand-written gate proof.** The applier checks that the digest matches the
  file; it cannot prove the gate actually ran. Someone with write access could
  fabricate a proof. Three things reduce this: the proof lands in a pull request
  as a reviewable diff, it records a gate database name that can be checked
  against Azure activity logs, and the apply-time object check fails a proof that
  does not describe the real migration. It is a real gap, and it is the one worth
  closing next.

  The route is already in this repository.
  `azure-pipelines-community-sql-proof.yml` and
  `scripts/run_community_disposable_sql_proof.py` stand up a digest-pinned
  `mcr.microsoft.com/mssql/server` container on the CI agent, run migrations
  against it, and destroy it — an in-pipeline disposable SQL runtime that needs
  no Azure SQL credential at all. A `SchemaGate` stage built on that substrate
  could generate the proof rather than verify a claimed one. Two caveats before
  anyone assumes it is a drop-in: a SQL Server container is not Azure SQL, so an
  Azure-hosted gate remains the more faithful rehearsal for anything touching
  serverless wake behaviour or Azure-specific features; and the proof must then
  be produced at pull-request time, not apply time, or the control moves to
  after the review that is supposed to inspect it.
- **A migration that is correct on an empty gate database and wrong on
  production.** The gate applies the declared prerequisite chain to a fresh
  Basic database with no member data. Production has data, different statistics,
  and a different size. A gate is a rehearsal, not a simulation.
- **Anyone who still has the production credential.** This path is the *supported*
  route, not a lock on the database. Nothing here prevents someone opening a SQL
  client and running whatever they like. What it does is make that visible
  afterwards: an unregistered ledger row is reported, and a registered migration
  applied out of band shows up as a state-record disagreement.
- **Data migrations and long locks.** Every migration here is additive DDL that
  completes in seconds. This path has no batching, no online-index strategy, no
  timeout budget, and no lock monitoring. A migration that rewrites a large table
  needs a different plan and should not be run through this path unexamined.
- **Point-in-time recovery.** The path takes no backup and records no restore
  point. Azure SQL's automatic PITR is what protects the data; if a migration
  needs a recorded restore point, record it separately and put it in the package
  evidence.
- **Approval configuration.** The environment approval lives in Azure DevOps,
  not in this repository, and this YAML cannot assert that it exists. Until the
  `peerslate-database-schema` environment has an approval check, the queue-time
  parameter is the only gate. See setup below.
- **The application/schema ordering question.** The path now prevents overlap,
  but it does not infer whether schema or code should go first. The package
  still has to name that order, and nothing yet checks that the deployed
  application matches the schema revision it expects.

## One-time setup before first production use

Neither can be done from this repository.

1. **Create the `peerslate-database-schema` environment** in Azure DevOps and
   add an approval check naming the people allowed to move production schema.
   Azure will otherwise auto-create the environment with no checks on first run.
2. **Define the secret pipeline variable `schemaConnectionString`** in the
   pipeline's Azure settings, holding the `peerslate-database` connection
   string. Mark it secret. Do not declare it in YAML.

Then run `schemaAction: report` once. It changes nothing, and it produces the
first honest `PRODUCTION_SCHEMA_STATE.md`.

## Evidence

The path was proven end to end against a throwaway database
`ps-migration-path-20260804` (Basic, server `peerslate`, created and deleted on
2026-08-04): eleven migrations gated including idempotency and rollback
rehearsal; a pending migration detected and applied; a re-run that was a genuine
no-op; a deliberately broken migration that failed closed mid-plan without
leaving state; a stale gate proof that blocked an apply; and the state record
detecting its own drift. `peerslate-database` was never connected to.
