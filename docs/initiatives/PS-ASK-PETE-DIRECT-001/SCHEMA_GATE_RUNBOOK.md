# PS-ASK-PETE-DIRECT-001 — schema gate and apply runbook

**Status: gate PASSED 2026-08-08T23:10:49Z on ps-ask-pete-direct-gate-202608082309 (operator: Pete; digest ec3d21d0...); proof recorded in the registry. Next: Part 4, the governed production apply.**

Parts 1–3 are done and are kept below as the record of what was run. **No
production database carries these tables yet** — that is Part 4, and it has not
happened.

Sitting-ready. Read it through before starting; parts 2 and 4 need credentials
only Pete holds, so this is a session you do together, not a background task.

| Part | Needs owner credentials? | Mutates anything? |
|---|---|---|
| 1. Pre-flight, offline | **No** | No |
| 2. Gate against a throwaway database | **Yes** — SQL admin, and creates/drops a disposable database | Only the throwaway database |
| 3. Record the proof in the registry | No | The repository (a PR) |
| 4. Governed production apply | **Yes** — pipeline queue rights **and** an approver on `peerslate-database-schema` | **Production schema** |
| 5. Post-apply verification | **Yes** — read-only production SQL | No |

---

## What is being applied

Two additive tables and three procedures. No existing object is altered,
dropped, or re-shaped, and nothing in the migration deletes a row.

| Object | |
|---|---|
| `dbo.recruiter_questions` | one question sent privately to one member |
| `dbo.recruiter_question_save_requests` | idempotency ledger — a key and a reference, no content |
| `dbo.usp_SubmitRecruiterQuestion` | anonymous-capable, consent-required write |
| `dbo.usp_ListRecruiterQuestionsForOwner` | bounded owner read |
| `dbo.usp_SetRecruiterQuestionStatusForOwner` | version-fenced new/read/archived |

Prerequisite chain the gate will apply first (computed, not guessed):

```
PS-PLAT-000, PS-PLAT-001, PS-PLAT-002, PS-PLAT-003, PS-PLAT-004,
PS-PLAT-005, PS-PLAT-006, PS-PLAT-007, PS-AUTH-001
```

Two properties worth knowing before you watch the gate run, because both look
alarming if you have not been told:

* **The rollback refuses while any question is stored.** That is deliberate —
  a stored question is a real person's message. In the gate database the
  tables are empty when the rollback rehearsal runs (the verifier rolls its own
  synthetic rows back inside one transaction), so the rehearsal passes. In
  production, once questions exist, `rollback` will refuse — and the correct
  answer to that refusal is to stop and decide explicitly, not to force it.
* **The forward migration is safe to re-run.** Every `CREATE TABLE` is guarded
  by `OBJECT_ID(...) IS NULL` and every procedure is `CREATE OR ALTER`. The
  gate proves this by applying it twice and checking the object inventory and
  ledger are unchanged.

---

## Part 1 — pre-flight, offline (no credentials, no database)

```bash
cd /path/to/portfolio            # or the worktree
venv/bin/python scripts/govern_sql_migrations.py check
```

**Expect:** exit 0, ending `Registry is internally consistent and every gate
proof matches.`

Before the gate ran, the entry appeared in that list as
`draft   PS-ASK-PETE-DIRECT-001  (no gate proof)`. **It now reads:**

```
  gated   PS-ASK-PETE-DIRECT-001  ec3d21d08bb1  ps-ask-pete-direct-gate-202608082309
```

If it says `STALE`, the T-SQL changed after the proof was recorded — stop and
re-gate; do not edit the proof. (`tests/ask_pete_direct/test_migration.py`
fails on exactly that, and on a hand-edited proof, so CI catches it too.)

Confirm the digest that is about to be gated:

```bash
venv/bin/python -c "
import sys; sys.path.insert(0,'scripts')
from migration_registry import load_registry, executable_sha256, ROOT
m = load_registry().get('PS-ASK-PETE-DIRECT-001')
print(executable_sha256(m.forward_path(ROOT)))"
```

**Expect** (as of this commit):

```
ec3d21d08bb186551b4b5053603c5cd5a9c536ded095a33f3e84e99d6f58c311
```

If it differs, the T-SQL changed since this runbook was written — that is fine,
but the value you record in part 3 must be the one the gate prints, never this
one copied forward.

Run the package suite once more so the gate is not chasing a code problem:

```bash
venv/bin/python -m pytest tests/ask_pete_direct/ -q
```

---

## Part 2 — gate against a throwaway database — **OWNER CREDENTIALS**

### 2a. Create the disposable database

Name it with today's date so it can never be confused with anything real. The
tool refuses `peerslate-database` and `peerslate-staging` outright, and a proof
recorded against either is rejected at load time.

```
ps-ask-pete-direct-gate-YYYYMMDDHHMM
```

Create it on the `peerslate` server through the Azure portal or `az sql db
create`. An inexpensive serverless/basic tier is right — it exists for minutes.

### 2b. Point the tool at it

The connection string is read from the environment and never printed, never
written to disk, and scrubbed out of any error. Put it in a local env file that
is **not** in the repository:

```bash
# ~/.peerslate-gate.env  (outside the repo; never commit)
AZURE_SQL_CONNECTIONSTRING=<the throwaway database's connection string>
```

### 2c. Run the gate

```bash
venv/bin/python scripts/govern_sql_migrations.py \
  --env-file ~/.peerslate-gate.env \
  --database ps-ask-pete-direct-gate-YYYYMMDDHHMM \
  --emit-evidence artifacts/ps-ask-pete-direct-001/gate.json \
  gate PS-ASK-PETE-DIRECT-001 \
  --expect-database ps-ask-pete-direct-gate-YYYYMMDDHHMM \
  --operator "Pete"
```

`--database` and `--expect-database` must be typed identically; the tool
refuses otherwise, so a gate cannot be aimed at a database by accident. The
rollback rehearsal runs by default — do **not** pass `--no-rehearse-rollback`.

**Expect**, in order:

```
Gate database: ps-ask-pete-direct-gate-YYYYMMDDHHMM on peerslate
Gating PS-ASK-PETE-DIRECT-001 (SQL FIles/Migrations/proposed/PS-ASK-PETE-DIRECT-001_recruiter_questions.sql)
Executable SHA-256: ec3d21…

  [1] prerequisites - PS-PLAT-000, PS-PLAT-001, …, PS-AUTH-001
  [2] forward apply - N object(s) created
  [3] re-apply is a no-op - objects and ledger unchanged
  [4] verification - PS-ASK-PETE-DIRECT-001_owner_isolation_verify.sql returned verified = 1
  [5] rollback rehearsal - N object(s) reversed
  [6] forward apply after rollback - ledger row restored

GATE PASSED for PS-ASK-PETE-DIRECT-001.
Registry entry gate proof:
{ …JSON… }
```

Step 4 is the one that matters most: the verifier provisions two synthetic
recipients, proves cross-recipient isolation on all three procedures,
per-recipient idempotency without overwrite, version fencing, forged-owner
canaries, that the submit never returns a question key, that no procedure
contains a `DELETE`, and that no question or contact text reaches audit
metadata — then rolls every synthetic row back.

**If step 4 fails**, stop. Do not record a proof, do not re-run with the
rollback rehearsal skipped, and do not apply anything. Read the THROW number in
the error — the verifier's numbers are `54000`–`54042` and each maps to one
named claim in the file.

### 2d. Drop the disposable database

Immediately, and confirm it is gone. Its only purpose is over.

---

## Part 3 — record the proof (repository change, ordinary PR)

Easiest and least error-prone: let the tool write it, by adding
`--update-registry` to the part 2c command. Otherwise paste the printed JSON
into the `PS-ASK-PETE-DIRECT-001` entry's `"gate"` field in
`SQL FIles/Migrations/registry.json`, replacing `null`.

The shape, matching the `PS-WORKSHOP-002` proof already in the file:

```json
"gate": {
  "executable_sha256": "<exactly what the gate printed>",
  "gated_at_utc": "<from the gate output>",
  "gate_database": "ps-ask-pete-direct-gate-YYYYMMDDHHMM",
  "gate_server": "peerslate",
  "prerequisites": [
    "PS-PLAT-000", "PS-PLAT-001", "PS-PLAT-002", "PS-PLAT-003",
    "PS-PLAT-004", "PS-PLAT-005", "PS-PLAT-006", "PS-PLAT-007",
    "PS-AUTH-001"
  ],
  "objects": [ "<exactly the list the gate printed>" ],
  "verification": "PS-ASK-PETE-DIRECT-001_owner_isolation_verify.sql returned verified = 1",
  "operator": "Pete"
}
```

Never hand-edit `executable_sha256`. It is the whole point of the proof: it
binds the recorded rehearsal to those exact bytes, and any later edit to the
T-SQL makes the applier refuse until it is re-gated.

Then, offline:

```bash
venv/bin/python scripts/govern_sql_migrations.py check
venv/bin/python -m pytest tests/ask_pete_direct/ tests/test_schema_migration_path.py -q
```

**DONE, 2026-08-08.** The entry moved from `draft` to
`gated   PS-ASK-PETE-DIRECT-001  ec3d21d08bb1  ps-ask-pete-direct-gate-202608082309`,
and — exactly as this runbook predicted —
`test_migration.py::RegistryTests::test_the_entry_is_registered_ungated`
failed, because it asserted `gate is None`. That guard existed so this
transition could not happen quietly; it fired, and was replaced rather than
deleted by `test_the_entry_carries_its_passed_gate_proof`, which now guards the
opposite risk: a recorded proof drifting from the file it vouches for, or being
hand-edited to look current. `test_the_tools_own_gate_check_agrees` asks the
applier's own `gate_status` for the same verdict rather than trusting the
test's re-implementation of it.

Both were verified to bite: tampering with the recorded digest, editing the
T-SQL without re-gating, and shortening the recorded prerequisite chain each
fail the suite.

That PR must merge before part 4. The pipeline applies from merged `main`.

---

## Part 4 — governed production apply — **OWNER CREDENTIALS + APPROVER**

Nothing applies automatically. A merge changes no database. The apply happens
only because a human queues the pipeline with a non-`none` schema action and an
approver releases the `peerslate-database-schema` environment.

### 4a. Queue the run

Run the `portfolio-site` pipeline on `main`, with parameters:

| Parameter | Value |
|---|---|
| `schemaAction` | `apply` |
| `schemaMigrationId` | `PS-ASK-PETE-DIRECT-001` |
| `schemaRollbackConfirm` | *(leave empty — apply, not rollback)* |

### 4b. Watch the validation and pre-flight jobs

`ValidateProductionOperationRequest` runs first and refuses a malformed
request. The pre-flight then reads the live ledger and refuses an unsafe queued
action **before** an approver is asked for anything. It runs:

```
govern_sql_migrations.py preflight apply \
  --migration-id PS-ASK-PETE-DIRECT-001 \
  --expect-database <schemaDatabaseName>
```

**Expect** a computed plan of exactly `PS-ASK-PETE-DIRECT-001` and no blockers.
A blocker here means stop — common causes: the ID is already in the ledger, the
gate digest no longer matches the merged file, or the plan resolved to more
than one migration (which would mean something else is also pending, and each
should be applied deliberately on its own run).

### 4c. Approve the environment

The `peerslate-database-schema` environment check pauses the run. Release it
only after reading the pre-flight output in that same run. This is the last
point at which nothing has changed.

### 4d. The apply

The job runs, with `--expect` and `--migration` both pinned so the plan cannot
silently widen:

```
govern_sql_migrations.py --azure-pipelines --emit-evidence …/schema/apply.json \
  --print-state apply \
  --migration PS-ASK-PETE-DIRECT-001 \
  --expect PS-ASK-PETE-DIRECT-001 \
  --expect-database <schemaDatabaseName> \
  --write-state
```

**Expect:** one migration applied, a ledger row written, and the run's evidence
artifact `schema/apply.json` attached. A no-op is reported loudly as a no-op —
it can never read as an apply. `docs/governance/PRODUCTION_SCHEMA_STATE.md` is
rewritten from the live ledger by `--write-state`; commit that change.

---

## Part 5 — post-apply verification — **OWNER CREDENTIALS, read-only**

Run against production. Nothing here mutates.

**1. The ledger row exists and nothing else moved:**

```sql
SELECT migration_id, applied_at_utc, description
FROM dbo.schema_migrations
WHERE migration_id = N'PS-ASK-PETE-DIRECT-001';
```
Expect exactly one row.

**2. Both tables and all three procedures exist:**

```sql
SELECT o.type_desc, s.name AS [schema], o.name
FROM sys.objects AS o
JOIN sys.schemas AS s ON s.schema_id = o.schema_id
WHERE o.name IN (
    N'recruiter_questions', N'recruiter_question_save_requests',
    N'usp_SubmitRecruiterQuestion', N'usp_ListRecruiterQuestionsForOwner',
    N'usp_SetRecruiterQuestionStatusForOwner')
ORDER BY o.type_desc, o.name;
```
Expect 5 rows: 2 `USER_TABLE`, 3 `SQL_STORED_PROCEDURE`.

**3. No delete or purge procedure was created — archive-only is structural:**

```sql
SELECT name FROM sys.procedures
WHERE name LIKE N'%RecruiterQuestion%'
  AND (name LIKE N'%Delete%' OR name LIKE N'%Purge%');
```
Expect **zero rows**.

**4. The store is empty — an apply must never carry data with it:**

```sql
SELECT
    (SELECT COUNT(*) FROM dbo.recruiter_questions) AS questions,
    (SELECT COUNT(*) FROM dbo.recruiter_question_save_requests) AS ledger_rows;
```
Expect `0, 0`.

**5. Run the verifier against production.** It is production-safe by
construction: everything it creates lives inside one transaction it always
rolls back, and its one non-scoped assertion is written against its own
run-unique sentinel text rather than "any row anywhere", so a real recipient's
questions cannot make it fail.

```
sqlcmd -S <server> -d <database> -G \
  -i "SQL FIles/Verification/PS-ASK-PETE-DIRECT-001_owner_isolation_verify.sql"
```
Expect one row: `verified = 1` with the summary sentence. Anything else — stop
and investigate before the feature is enabled.

**6. Confirm the application still does not reach any of it:**

The blueprint is unregistered and the flag is off, so applying the schema
changes no runtime behaviour at all. Confirm nothing moved:

```bash
curl -si https://peerslate.com/api/ask-pete/direct-question -X POST | head -1
curl -si https://peerslate.com/owner/ask-pete-inbox | head -1
```
Expect a 404 from both — the same 404 any nonexistent path returns.

---

## Order of the remaining legs

```
gate + registry PR (parts 1-3)
      ↓
production apply (part 4-5)          ← schema exists, still unreachable
      ↓
registration leg (REGISTRATION_LEG_SPEC.md) + deploy   ← routes exist, still 404
      ↓
PEERSLATE_OWNER_USER_KEYS set to exactly one key
      ↓
Pete reviews the consent copy in the live preview
      ↓
PEERSLATE_ASK_PETE_DIRECT_ENABLED=true                 ← live
```

Schema before registration, deliberately: if the routes existed before the
tables did, a send would answer an honest 503 — recoverable, but it means a
real recruiter's question was lost. Applying the schema first removes that
window entirely.
