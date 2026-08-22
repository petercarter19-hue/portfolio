# PS-INTERVIEW-AI-EXTRACT-001 — governed release plan

_Prepared 2026-08-21 under Pete's authorization to "create the pull
request and prepare the governed release plan", and **corrected the same
day** after the release-plan review returned CORRECTION REQUIRED
(R1–R7). **This document executes nothing.** Every phase after Phase 1
names the authorization it still requires._

## 0. Authorization boundary

| Authorized (Pete, 2026-08-21) | Explicitly withheld |
|---|---|
| Create the pull request (done — PR 564) | Applying SQL / running the migration |
| Prepare and correct this release plan | Changing production configuration |
| | Merging any pull request |
| | Deploying |
| | Enabling telemetry retention |
| | Any provider call, token use, or spend |
| | **Creating or merging the additional dark-infrastructure PR described in §3** |

Nothing below may be executed without the specific authorization named in
its phase. A merge is not a deployment, and a deployment is not
enablement. Describing the two-stage delivery shape in §3 is a
documentation act only; it confers no authority to create or merge that
second pull request.

## 1. Review state and candidate facts (R4)

| Fact | Value |
|---|---|
| Implementation accepted at | `dd545348939a668e4d4ff375526d689fa4174f89` |
| Frozen candidate within it | `abefce2ba2c752dc5c76c944d64179bcda07152f` |
| Prior rejected release-plan tip | `ba80d40982885e3dbcfd7a6a05bad5f10e3c3d0d` |
| Branch | `work/2026-08-20-interview-ai-extract-001` |
| Base | `origin/main` `424f2efe` reconciled, no rebase |
| Release set id | `1b9441a052593a2a17837572b659325c7ca3d0dfc46f018e9283949ee7caa935` |
| Contracts / anchors | `interview-contracts@7`, chain `@1→@7` |
| `activated_at` | `null` — recording the release set is the only release fact this candidate creates |

This document does not name its own commit. A commit cannot contain its
own SHA, so any "present tip" written here would be false the moment it
was created. **The exact corrected documentation tip is bound externally**
— by the package-manager verdict and the targeted independent-review
verdict recorded against it, not by a self-reference inside the file.

Review outcomes:

- **Codex package-manager review: PASS**
- **Grok independent exact-candidate review: PASS**
- **Release-plan review: CORRECTION REQUIRED** (R1–R7) — corrected by
  this document.
- **PR 564 remains non-completable** pending corrected sequencing and new
  authority. It stays open with auto-complete disabled.

The accepted implementation is unchanged by this correction: no runtime
code, bundle, identity, migration byte, test, or B1–B6 evidence file is
modified. This is a documentation-only correction.

Evidence already recorded: `01_FROZEN_CONTRACTS.md`,
`02_PARITY_EVIDENCE.md`, `03_ROLLBACK_EVIDENCE.md`,
`05_SQL_DISPOSABLE_PROOF.json` (88/88, throwaway created and deleted),
`07_TRIPWIRE_MUTATION_MATRIX.json` (39/39),
`08_RUNTIME_LOCK_PROOF.json`, `09_PARITY_REPLAY_RESULT.json` (40/40).

## 2. The accepted order, restored (R1)

**Telemetry does not ship until the table, the procedure, the access
rule, and the scheduled purge path all exist.** The frozen C8 record
requires telemetry infrastructure to be in place *before* the runtime is
deployed, and the accepted architecture says the same.

The earlier draft of this plan permitted:

> runtime merge/deployment → telemetry schema → retention

**That sequence is withdrawn and rejected.** The reasoning behind it —
that a missing telemetry table is tolerated because the bounded append
fails content-free and the member response is unchanged — was a
category error. Append-failure safety is a *failure-handling property*
of the runtime. It is not authority to deploy while required operational
controls are absent. A control that is designed to degrade safely is not
a control that may be skipped.

The correct resolution of the constraint that produced the error — the
migration file reaches `main` only when a pull request carrying it is
merged — is not to reorder the release. It is to split the delivery, so
that the infrastructure lands first without touching the Interview
runtime. That shape is §3.

## 3. Required two-stage delivery shape (R2)

**PR 564 cannot be completed in its present combined form.** It carries
the runtime extraction and the telemetry infrastructure together, and
completing it would deploy the runtime at the same moment the
infrastructure arrives, which the accepted order forbids.

A separately authorized delivery mechanism must preserve this order:

1. **Land dark telemetry infrastructure without changing the Interview
   runtime:**
   - the migration proposal and its registry receipt;
   - the maintenance script and the independently gated pipeline stage;
   - the required operational tests;
   - **no Interview provider-dispatch change.**
2. **Apply the governed telemetry migration.**
3. **Bind and verify the append identity.**
4. **Provision and verify the independent maintenance identity and the
   scheduled 90-day purge path.**
5. **Enable and verify scheduled retention**
   (`interviewTelemetryMaintenanceEnabled=true`).
6. **Set** `PEERSLATE_INTERVIEW_ACTIVE_RELEASE_SET` **to**
   `1b9441a052593a2a17837572b659325c7ca3d0dfc46f018e9283949ee7caa935`
   **while the legacy runtime remains deployed.**
7. **Only then merge/deploy the accepted runtime candidate.**

**Runtime deployment is prohibited while retention remains disabled.**
Retention must be operative *before* telemetry starts being written, not
after — otherwise the first rows would accumulate with no proven purge
path, which is exactly the "ship telemetry without its operational
controls" failure this order exists to prevent.

**Recommended mechanism:** a separately reviewed dark-infrastructure pull
request, followed by the runtime pull request. Recording that
recommendation here does **not** authorize creating or merging the
additional pull request; that requires its own explicit authority.

If a different governed mechanism is proposed instead, it must prove that
the exact reviewed migration can be applied before runtime deployment
**without bypassing the main-only schema controls** (`SchemaApply`
requires `Build.SourceBranch == refs/heads/main` and a non-default
`schemaAction`, released by an approver on the
`peerslate-database-schema` environment).

Step 6 keeps the C8 configuration-before-deploy rule intact and is the
step that protects availability: the legacy runtime does not read that
key, so setting it changes nothing observable, while deploying the
candidate without it would answer a fail-closed 503 on all four Interview
endpoints by design.

## 4. Phase 1 — Pull request and validation *(authorized; executed)*

- PR **564** opened, `work/2026-08-20-interview-ai-extract-001` → `main`,
  **auto-complete not set**, no merge conflicts. It **remains open and
  non-completable**.
- `main` carries a blocking **Build** validation policy, so opening the
  PR queues a validation run.
- **Verified safe:** a PR validation build cannot deploy or move schema.
  `ProductionWebDeploy` and `SchemaApply` both require
  `Build.SourceBranch == refs/heads/main`; a PR build runs as
  `refs/pull/<id>/merge`. `SchemaApply` additionally requires a
  non-default `schemaAction`. The pipeline's only `trigger:` branch is
  `main`.

### Phase 1 result (executed 2026-08-21)

Validation run **1368** on `refs/pull/564/merge` (reason `pullRequest`):
**succeeded**. Stage outcomes confirm the safety prediction empirically —
one stage ran, nine were skipped:

| Result | Stage |
|---|---|
| succeeded | Build |
| skipped | Deploy the production application |
| skipped | Read schema state before any approval is requested |
| skipped | Run the approved schema operation |
| skipped | Deploy isolated candidate |
| skipped | Verify isolated candidate |
| skipped | Exercise and enforce candidate stop |
| skipped | Report that production was not deployed |
| skipped | Run independently gated Community maintenance |
| skipped | Run independently gated Interview telemetry retention |

Nothing was deployed, no schema was read or moved, and no telemetry
retention ran. The four Community-lane failures seen on the Windows
development machine did not appear in CI, confirming they are
environmental to that machine. Run **1369** re-validated the
documentation-only tip and also succeeded; each later documentation
commit supersedes the previous run.

## 5. Phase 2 — Dark telemetry infrastructure *(WITHHELD — needs new authority)*

Per §3 step 1. Lands the migration proposal and registry receipt, the
maintenance script, the independently gated pipeline stage, and the
required operational tests, **with no Interview provider-dispatch
change**. The Interview runtime behaviour is byte-identical before and
after this phase.

- The independently gated stage stays default-off
  (`interviewTelemetryMaintenanceEnabled`), and its schedule triggers
  nothing operative.
- **Verify:** CI green; Interview routes unchanged; no runtime diff.
- **Rollback:** revert the dark-infrastructure change; nothing operative
  depended on it.

## 6. Phase 3 — Governed telemetry migration *(WITHHELD)*

Per §3 step 2. Apply `PS-INTERVIEW-AI-EXTRACT-001_telemetry.sql` through
the governed path only: queue the pipeline with a non-default
`schemaAction`, with an approver releasing the
`peerslate-database-schema` environment. Schema never moves because a
pull request merged.

- Already gated: disposable-database proof 88/88, gate receipt in
  `SQL FIles/Migrations/registry.json`, gate database
  `ps-interview-extract-gate-b6-20260821` created **and deleted**.
- **Any later edit to the migration bytes invalidates that receipt and
  requires a fresh gate on a new throwaway database.**
- **Verify (provider-free):** schema objects exist as recorded — table,
  both procedures, constraints, index.
- **Rollback:** the rollback file refuses, transactionally, to drop a
  telemetry table holding any rows (`THROW 50090`). Retiring a non-empty
  production table is its own separately authorized retention-safe
  operation.

## 7. Phase 4 — Append identity *(WITHHELD)*

Per §3 step 3. Bind and verify the application's append identity.

- **Verify (provider-free):** stored-procedure behaviour and permission
  separation — the append role can execute the append procedure and
  **cannot** select, insert directly, or purge; a hostile-value probe is
  rejected with the recorded named errors.

## 8. Phase 5 — Maintenance identity and purge path *(WITHHELD)*

Per §3 step 4. Provision and verify the independent maintenance identity
and the scheduled 90-day purge path.

- **Verify (provider-free):** the maintenance role can execute the purge
  procedure and **cannot** append or delete directly; purge readiness is
  demonstrated with bounded batch behaviour and correct retention
  boundary. The schedule is still default-off at the end of this phase;
  enabling it is Phase 6, which must complete before any runtime deploy.

## 9. Phase 6 — Enable and verify scheduled retention *(WITHHELD — separate authority)*

Per §3 step 5, and **before** production configuration. Runtime
deployment is prohibited while retention remains disabled.

1. Set `interviewTelemetryMaintenanceEnabled=true`.
2. Confirm the dedicated Interview maintenance identity is bound (its own
   workload identity, not Community's, not the application's append
   identity).
3. Confirm the nightly schedule (`Interview telemetry retention nightly`,
   cron `41 2 * * *`) is operative and **independently isolated from
   Community** — both schedule-gated stages check
   `Build.CronSchedule.DisplayName`, so an Interview run must not trigger
   Community maintenance and vice versa.
4. Perform a **provider-free, bounded readiness execution** of the purge
   path.
5. **Verify (provider-free):** the run's report is content-free, it
   applies the correct 90-day boundary, and its bounded batch counts are
   reported truthfully.
6. **Stop** if enablement cannot be proven, if the identity is not the
   dedicated Interview one, if the schedules are not isolated, or if the
   bounded execution cannot be completed and verified. Do not proceed to
   Phase 7 or Phase 8.

- **Rollback:** set the enablement variable back to false; the stage
  returns `{"result": "disabled"}` and deletes nothing.

## 10. Phase 7 — Production configuration *(WITHHELD)*

Per §3 step 6, and only after retention is enabled and verified. Set,
**while the legacy runtime is still deployed**:

```
PEERSLATE_INTERVIEW_ACTIVE_RELEASE_SET = 1b9441a052593a2a17837572b659325c7ca3d0dfc46f018e9283949ee7caa935
```

- The legacy runtime does not read this key, so this changes nothing
  observable. Setting an App Service setting restarts the process; the
  legacy runtime restarts unchanged.
- **Verify (provider-free health and refusal checks only):**
  - application configuration reads back exactly the recorded 64-hex id;
  - the application is healthy after the restart (`/healthz`);
  - provider-free refusal routes still answer as recorded — a non-JSON
    content type → `415`, a cross-site request → `403`, and
    `POST /api/interview/coach` → `410`;
  - `GET /interview-studio` renders;
  - the rest of the site is unaffected.
- **No valid provider-eligible request is issued in this phase.** No
  token use and no spend is authorized here.
- **Rollback:** remove the setting. Legacy is unaffected either way.

## 11. Phase 8 — Runtime merge and deploy *(WITHHELD)*

Per §3 step 7, and only after Phases 2–7 are complete and verified —
including Phase 6, without which runtime deployment is prohibited.

- Complete the runtime pull request with the required merge strategy
  (squash).
- The squash commit message **must not** contain `[skip ci]`: this is a
  runtime change and must run the normal pipeline.
- The merge triggers Build → `ProductionWebDeploy` automatically.
- Do not manually queue a fallback while an automatic run for the same
  `main` SHA is active.

**Verify after the run reports success — a merge is not a deployment
(all provider-free):**

1. Pipeline run green, including the vendored install and staged
   installed-byte verification (B3 runtime lock).
2. **Boot readiness, from startup logs only (R9).** Readiness is
   established from the guarded runtime's own startup line, never from an
   HTTP probe. A request malformed enough to stay provider-free (`415`,
   `403`) short-circuits *before* release resolution and therefore cannot
   distinguish `ready` from `service_not_configured`; a request
   well-formed enough to distinguish them is provider-eligible the moment
   the state is `ready`. The check is therefore:
   1. Inspect the production application/process startup logs for the
      exact deployment and restart.
   2. Verify the normalized, content-free line emitted by
      `services/interview_ai/boot.py`:

      ```
      interview boot state frozen: ready
      ```

   3. If production runs multiple active instances or workers, reconcile
      the platform instance inventory and require `ready` evidence for
      **every** newly started instance or worker that can receive
      Interview traffic.
   4. **Stop** if any startup reports `service_not_configured`; if the
      `ready` line is absent; if logging does not capture the existing
      INFO-level line; or if instance coverage cannot be proven.
   5. **Do not** compensate for missing log evidence by issuing a
      well-formed Interview request, by changing logging configuration,
      or by making a provider call. Return for a separately governed
      observability resolution instead.

   **No well-formed provider-eligible Interview POST is used to establish
   boot readiness.**
3. Provider-free refusal routes answer exactly as recorded — these
   confirm the HTTP contract only, and are **not** evidence of boot
   readiness:
   - `POST /api/interview/review` with a non-JSON content type → `415`
     with the exact legacy copy;
   - cross-site refusal → `403` with the exact legacy copy;
   - `POST /api/interview/coach` → `410` retired-endpoint contract;
   - `GET /interview-studio` renders.
4. The rest of the site is untouched (homepage, Community, owner routes).

**Rollback:** redeploy the previous `main` artifact. The configuration
from Phase 7 may stay set — the legacy runtime ignores it. Telemetry rows
already written age out under the 90-day retention; nothing member-facing
reads them.

## 12. Verification is provider-free (R3, R7)

No phase in this plan authorizes a provider call. Every verification
above is limited to:

- schema objects;
- stored-procedure behaviour;
- permission separation;
- application configuration;
- purge readiness;
- deployment health, boot readiness read from startup logs, and
  provider-free refusal routes.

**No well-formed provider-eligible Interview POST is used to establish
boot readiness**, and no missing log evidence may be compensated for by
issuing one.

**Any real provider smoke, token use, or spend remains a separate
explicit gate** requested and authorized on its own terms. No phase here
may be read as permitting "one real Interview call".

## 13. Stop conditions

Stop and return to Pete/Codex if any of these occur:

- PR validation red for any reason other than a known-environmental
  Community-lane failure.
- Any proposal to complete PR 564 in its present combined form.
- Any proposal to deploy the runtime before Phases 2–7 are complete.
- **Any proposal to deploy the runtime while retention is disabled**, or
  while the retention enablement of Phase 6 cannot be proven.
- After Phase 8, the startup logs report
  `interview boot state frozen: service_not_configured`, omit the
  `ready` line entirely, do not capture that INFO-level line, or cannot
  be shown to cover every instance or worker able to receive Interview
  traffic. (Boot readiness is judged from startup-log evidence, never
  from an Interview endpoint returning or not returning a 503.)
- Any Interview response, status, or copy differs from the recorded
  parity oracle.
- Any guarded-identity or anchor verification failure at any point.
- The migration bytes differ from the gated receipt.
- Any instruction to reorder these phases so that the candidate deploys
  before its configuration is set, before telemetry infrastructure
  exists, or before retention is enabled and verified.

## 14. What this plan explicitly does not do

No SQL applied, no production configuration changed, no merge, no
deployment, no telemetry enablement, no provider call, no evaluation
spend, no additional pull request created, and no claim that any of the
above has occurred.
