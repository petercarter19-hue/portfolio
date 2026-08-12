# PS-OPPSLATE-004 — schema gate runbook

**Status: PERMISSION-REPAIR GATE PASSED. `registry.json` carries the proof
emitted at 2026-08-12T13:27:59Z from
`ps-oppslate-004-perm-202608121325`. The exact executable SHA-256 is
`f4752c0e9cf176d26bd4239a5cf13bbc99e7614fa1da7fae6087705d79acb73a`.
The exact forward also passed as a production-shaped `db_ddladmin` principal
with zero `SELECT` on both protected existing tables. Governed production run
836 attempted Part 4 from the prior bytes, failed on that missing `SELECT`, and
rolled back transactionally; the ledger stayed at 26 and 004 remained absent.
The repaired Part 4 re-apply and Part 5 verification remain pending fresh
exact-SHA review, PR/CI, and recorded release authority.**

Mirrors `docs/initiatives/PS-ASK-PETE-DIRECT-001/SCHEMA_GATE_RUNBOOK.md`
exactly — the same tool, the same five-part shape, and the same credential
caution — adapted to this migration's own objects and prerequisites. The
Part 2 run used the existing authorized Azure CLI/Entra session; no password
was requested, copied, or stored. The emitted proof, not hand-authored values,
is authoritative.

| Part | Needs owner credentials? | Mutates anything? |
|---|---|---|
| 1. Pre-flight, offline | **No** | No |
| 2. Gate against a throwaway database | **Yes** — SQL admin, and creates/drops a disposable database | Only the throwaway database |
| 3. Record the proof in the registry | No | The repository (a PR) |
| 4. Governed production apply | **Yes** — pipeline queue rights **and** an approver on `peerslate-database-schema` | **Production schema** |
| 5. Post-apply verification | **Yes** — production SQL execute/write authority | **Yes, temporarily** — synthetic rows and procedure calls inside an always-rolled-back transaction; no rows are committed, but locks/log activity occur and identity counters can advance |

Part 4 applies the schema and Part 5 validates it with rollback-contained
synthetic writes — this package's blueprint stays
unregistered and its flag stays default-false until a later slice (R5)
wires registration (see the package README's "R2+ outlook"). Applying the
schema early is deliberate and safe: it removes the window where routes
exist before the tables do (the same reasoning
`SCHEMA_GATE_RUNBOOK.md`'s "Order of the remaining legs" section documents
for the sibling package).

---

## What is being gated

Three new tables (one R1 actually writes; two prove their shape once for
R2, per the architecture's explicit instruction), three nullable additive
columns on existing tables, two new procedures, and a hash-stamped takeover
of two existing procedures so they learn the three new tables. Nothing
below drops, alters the shape of, or mutates a row in any PS-OPPSLATE-001/
002/003 object.

| Object | Kind | Notes |
|---|---|---|
| `dbo.opportunity_source_identities` | table, new | R1 writes this one — image 05 section A |
| `dbo.opportunity_requirement_review_events` | table, new | R2-consumed; shape-only in R1 |
| `dbo.opportunity_member_takes` | table, new | R2-consumed; shape-only in R1 |
| `dbo.opportunity_analyses.evidence_snapshot_sha256` | column, new (nullable) | R2 currency model |
| `dbo.opportunity_analyses.confirmed_requirements_ordinal` | column, new (nullable) | R2 currency model |
| `dbo.opportunity_requirement_sets.member_confirmed_ordinal` | column, new (nullable) | R2 currency model |
| `dbo.usp_SaveOpportunitySourceIdentityForOwner` | procedure, new | fenced on `opportunity_sources.row_version` |
| `dbo.usp_GetOpportunitySourceIdentityForOwner` | procedure, new | owner-scoped read; `None` on no row |
| `dbo.usp_PurgeExpiredOpportunityWorkingData` | procedure, **takeover** | re-stamped `PS_OPPSLATE_004_DEFINITION_HASH`; OS-3's own `PS_OPPSLATE_002_DEFINITION_HASH` stamp is left in place, now describing a superseded body |
| `dbo.usp_DeleteOpportunityWorkingSessionForOwner` | procedure, **takeover** | same re-stamp treatment |

Prerequisite chain the gate computes (declared, not guessed, by the tool —
confirm with Part 1 below rather than trusting this table if the two ever
disagree):

```
PS-OPPSLATE-001, PS-OPPSLATE-002, PS-OPPSLATE-003
```

`registry.json`'s own `requires` array for `PS-OPPSLATE-004` names exactly
these three; `scripts/govern_sql_migrations.py` resolves each of those
transitively (platform/auth baseline included) the same way it did for
every other gated migration in this file.

Two properties worth knowing before the gate runs:

* **The rollback refuses while any source identity, requirement review
  event, or member take row exists.** In the gate database these tables are
  empty when the rollback rehearsal runs (the verifier's synthetic rows are
  written and rolled back inside one transaction — see the verifier's own
  final `ROLLBACK TRANSACTION`), so the rehearsal passes. In production,
  once real rows exist, `rollback` will refuse — the correct response is to
  stop and decide explicitly, never to force it.
* **The forward migration is safe to re-run.** Every `CREATE TABLE` is
  guarded by `OBJECT_ID(...) IS NULL`, every `ALTER TABLE ... ADD` column is
  guarded by a `COL_LENGTH(...) IS NULL` check, and every procedure is
  `CREATE OR ALTER`. The gate proves this by applying the migration twice
  and checking the object inventory is unchanged the second time.

---

## Part 1 — pre-flight, offline (no credentials, no database)

```bash
cd /path/to/portfolio            # or this worktree
venv/bin/python scripts/govern_sql_migrations.py check
```

**Expect:** exit 0. Before the recorded gate, `PS-OPPSLATE-004` read as
`draft  PS-OPPSLATE-004  (no gate proof)`. It now reads as `gated` with the
`f4752c0e9cf1` digest prefix and the successful disposable database name.

Confirm the digest that is about to be gated:

```bash
venv/bin/python -c "
import sys; sys.path.insert(0,'scripts')
from migration_registry import load_registry, executable_sha256, ROOT
m = load_registry().get('PS-OPPSLATE-004')
print(executable_sha256(m.forward_path(ROOT)))"
```

The value this prints is whatever the file's current bytes hash to — record
it nowhere until the actual gate run in Part 2 prints the same value back;
that agreement is what proves the gate ran against the file that is
actually about to be recorded, not a stale copy. If a later edit changes
the T-SQL, the digest changes and the migration must be re-gated; do not
carry an old digest forward.

Run the package suite once more so the gate is not chasing a code problem:

```bash
ANTHROPIC_API_KEY=placeholder-not-a-real-key \
  venv/bin/python -m unittest tests.test_opportunity_slate_v2 tests.test_opportunity_slate_v2_migration -v
```

---

## Part 2 — gate against a throwaway database — **OWNER CREDENTIALS**

### 2a. Create the disposable database

Name it with today's date so it can never be confused with anything real.
The tool refuses `peerslate-database` and `peerslate-staging` outright, and
a proof recorded against either is rejected at load time.

```
ps-oppslate-004-gate-YYYYMMDDHHMM
```

Create it on the `peerslate` server (Azure portal or `az sql db create`).
An inexpensive serverless/basic tier is right — it exists for minutes.

### 2b. Point the tool at it

The connection string is read from the environment and never printed,
never written to disk, and scrubbed out of any error. Put it in a local
env file that is **not** in the repository:

```bash
# ~/.peerslate-gate.env  (outside the repo; never commit)
AZURE_SQL_CONNECTIONSTRING=<the throwaway database's connection string>
```

### 2c. Run the gate

```bash
venv/bin/python scripts/govern_sql_migrations.py \
  --env-file ~/.peerslate-gate.env \
  --database ps-oppslate-004-gate-YYYYMMDDHHMM \
  --emit-evidence artifacts/2026-08-11-opportunity-slate-v2/PS-OPPSLATE-004-gate.json \
  gate PS-OPPSLATE-004 \
  --expect-database ps-oppslate-004-gate-YYYYMMDDHHMM \
  --operator "Pete"
```

`--database` and `--expect-database` must be typed identically; the tool
refuses otherwise. The rollback rehearsal runs by default — do **not** pass
`--no-rehearse-rollback`.

**Expect**, in order:

```
Gate database: ps-oppslate-004-gate-YYYYMMDDHHMM on peerslate
Gating PS-OPPSLATE-004 (SQL FIles/Migrations/proposed/PS-OPPSLATE-004_opportunity_slate_replacement.sql)
Executable SHA-256: …

  [1] prerequisites - the complete transitive chain ending in PS-OPPSLATE-001, PS-OPPSLATE-002, PS-OPPSLATE-003
  [2] forward apply - N object(s) created
  [3] re-apply is a no-op - objects and ledger unchanged
  [4] verification - PS-OPPSLATE-004_owner_isolation_verify.sql returned verified = 1
  [5] rollback rehearsal - N object(s) reversed
  [6] forward apply after rollback - ledger row restored

GATE PASSED for PS-OPPSLATE-004.
Registry entry gate proof:
{ …JSON… }
```

Step 4 is the one that matters most. The verifier provisions
two synthetic owners, confirms both sources, proposes one requirement
statement each via the unchanged OS-2 procedure, attaches synthetic
`opportunity_requirement_review_events` and `opportunity_member_takes` rows
directly (there is no R1 procedure that writes those two tables yet — see
the forward migration's own header), then proves: identity save/read
cross-owner isolation with forged-key canaries; a repeated identity save
upserts one row per source version rather than duplicating; identity save
never touches write-once employer wording or the confirmation triple; the
purge and explicit-delete takeovers each reach all three new v2 child
tables and remove only the acting owner's rows, with an equivalent second
owner's rows dynamically checked after each operation; forged-key and
stale-rowversion deletes are refused without changing the target owner's
rows; and no employer, response, or identity wording reaches `audit_events`.
Everything it creates lives inside one transaction the verifier itself rolls
back at the end (`ROLLBACK TRANSACTION`, the script's last statement before
its closing `CATCH`). This prevents committed synthetic rows, but the verifier
is not read-only: it executes mutating procedures and direct DML, takes locks,
writes the transaction log, and can advance identity counters even though the
transaction rolls back.

**If step 4 fails**, stop. Do not record a proof, do not re-run with the
rollback rehearsal skipped, and do not apply anything. The verifier uses
`53880`–`53899`, `53902`–`53919`, and `53930`–`53944`; the forward migration
uses `53800`–`53807`; the rollback uses `53820`–`53826`. Each maps to one
named claim in its file — read the number, find the `THROW`, and read the
comment above it.

### 2d. Drop the disposable database

Immediately, and confirm it is gone. Its only purpose is over.

---

## Part 3 — record the proof (repository change, ordinary PR)

Easiest: add `--update-registry` to the Part 2c command and let the tool
write it. Otherwise paste the printed JSON into the `PS-OPPSLATE-004`
entry's `"gate"` field in `SQL FIles/Migrations/registry.json`, replacing
`null`, matching the shape already used by every other gated entry in that
file (for example `PS-ASK-PETE-DIRECT-001`, `PS-COMMUNITY-REVIVAL-001`):

```json
"gate": {
  "executable_sha256": "<exactly what the gate printed>",
  "gated_at_utc": "<from the gate output>",
  "gate_database": "ps-oppslate-004-gate-YYYYMMDDHHMM",
  "gate_server": "peerslate",
  "prerequisites": [ "<exactly the complete transitive list the gate printed>" ],
  "objects": [ "<exactly the list the gate printed>" ],
  "verification": "PS-OPPSLATE-004_owner_isolation_verify.sql returned verified = 1",
  "operator": "Pete"
}
```

Never hand-edit `executable_sha256`, `gated_at_utc`, or `objects`. The
whole point of the proof is that it binds the recorded rehearsal to those
exact bytes; any later edit to the T-SQL makes the applier refuse until it
is re-gated (`tests/test_opportunity_slate_v2_migration.py` and
`scripts/govern_sql_migrations.py check` both catch a hand-edited or stale
proof — see that suite's own registry/gate tests, which mirror
`tests/ask_pete_direct/test_migration.py`'s).

Then, offline:

```bash
venv/bin/python scripts/govern_sql_migrations.py check
ANTHROPIC_API_KEY=placeholder-not-a-real-key \
  venv/bin/python -m unittest discover
```

### 2026-08-12 execution record

The gate was deliberately fail-closed. Four fresh Basic databases exposed
verifier-only defects before any proof was recorded:

1. `...2305`: inline `CONCAT(...)` expressions were invalid as stored-procedure
   `EXEC` arguments.
2. `...2307`: confirmation used the pre-identity-save source rowversion.
3. `...2309`: expiry setup backdated only `expires_at_utc` and violated the
   existing expiry check constraint.
4. `...2311`: the purge assertion expected Owner B's identity row without
   creating it first.

Each defect received a focused regression test. Each failed disposable
database was deleted and confirmed absent before the next one was created.
The fifth fresh database, `ps-oppslate-004-gate-202608112314`, passed the
then-current six-step gate. Exact-SHA review identified that its legitimate
explicit-delete flow had no surviving second owner and that the generic gate
runner inferred its rollback object count from the forward count instead of
measuring the post-rollback catalog. A sixth fresh database,
`ps-oppslate-004-gate-202608112343`, therefore ran the strengthened verifier
at SHA-256
`f0d768340721cb93133b0335130a2a8203695c4bd6d15f83479884b09cd04710`
and passed all six steps. The governed rollback command then ran the rollback
file at SHA-256
`f4ac53dfa0c53454afe67dd9836830cbe433391241cbfb48ac47cb16f946a9b7`
and removed exactly the same 42 catalog objects recorded by the forward gate;
a read-only catalog
query confirmed the three additive columns and two new procedures absent,
the 004 procedure fingerprints absent, and both takeover procedures restored
to their exact PS-OPPSLATE-002 fingerprints. The sixth gate emitted the
authoritative registry proof and the supplemental evidence is preserved in
`PS-OPPSLATE-004-rollback-proof.json` and
`PS-OPPSLATE-004-post-rollback-state.json`. Every disposable database was
deleted and confirmed absent. No production database was opened or mutated by
Parts 1-3.

---

## Part 4 — governed production apply — **OWNER CREDENTIALS + APPROVER**

Nothing applies automatically. A merge changes no database. Queue the
`portfolio-site` pipeline on `main` with `schemaAction=apply`,
`schemaMigrationId=PS-OPPSLATE-004`, `schemaRollbackConfirm` left empty.
`ValidateProductionOperationRequest` and the pre-flight job run first and
refuse an unsafe queued action before an approver is asked for anything;
release the `peerslate-database-schema` environment check only after
reading that output. See `SCHEMA_GATE_RUNBOOK.md` Part 4 for the exact
command shapes — identical here, `--migration-id`/`--migration`/`--expect`
all set to `PS-OPPSLATE-004`.

---

## Part 5 — post-apply verification — **OWNER CREDENTIALS, TRANSACTIONAL WRITES**

Run against production only under recorded release authority. Steps 1–3 and 5
are read-only. Step 4 is not: it executes mutating procedures and direct DML
inside an outer transaction that always rolls back. It commits no synthetic
rows, but it can take locks, write transaction-log records, and advance
identity counters. The executing identity therefore needs the same bounded
execute/write permissions proven by the gate, not a read-only login.

1. **The ledger row exists:** `SELECT migration_id, applied_at_utc FROM
   dbo.schema_migrations WHERE migration_id = N'PS-OPPSLATE-004';` — expect
   one row.
2. **All ten objects from the table above exist** (3 tables, 2 procedures
   new, 2 procedures taken over — the takeovers already existed, so
   confirm via the extended-property stamp instead of an object count:
   `SELECT OBJECT_NAME(major_id), CONVERT(nvarchar(64), value, 2) FROM
   sys.extended_properties WHERE name = N'PS_OPPSLATE_004_DEFINITION_HASH';`
   — expect two rows).
3. **Every new/altered table is empty:** an apply must never carry data
   with it. `opportunity_source_identities`,
   `opportunity_requirement_review_events`, and `opportunity_member_takes`
   all read `0`.
4. **Run the transactional verifier against production** (synthetic rows are
   always rolled back, but the operational effects above still apply — see
   Part 2c):
   ```
   sqlcmd -S peerslate.database.windows.net -d peerslate-database -G \
     -i "SQL FIles/Verification/PS-OPPSLATE-004_owner_isolation_verify.sql"
   ```
   Expect one row: `verified = 1` with the detail sentence. Anything else —
   stop and investigate.
5. **Confirm the application still does not reach any of it:** the
   blueprint is unregistered and the flag is off, so applying the schema
   changes no runtime behaviour. `curl -si https://peerslate.com/opportunity-slate`
   still answers whatever the **legacy** room answers (unchanged) — this
   migration's own routes are not reachable at any path yet.

---

## Order of the remaining legs

```
this gate + registry PR (parts 1-3)
      ↓
production apply (part 4-5)          ← schema exists, still unreachable
      ↓
R2's own additive migration (the eight deferred procedures, informed by
R2's actual route/service contracts)
      ↓
R5 cutover: app.py registers this blueprint, flag flips, two-mode audit
gate, live smoke (package README, "R2+ outlook")
```
