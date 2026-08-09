# PS-AGENT-OPERATIONS-001 — routine deploys stop asking for permission

_Delivery path: Protected. Opened 2026-08-09. Scope: `azure-pipelines.yml`, its
tests, and the two documents that describe the schema path. No Azure
environment or check configuration is changed by this package._

## The defect

`azure-pipelines.yml` put the production web deployment and the governed schema
operation in a single stage, `ProductionOperation`. That stage referenced two
environments:

| Environment | Checks it carries |
|---|---|
| `peerslate-pete` (`$(environmentName)`) | One exclusive lock (id 14). Serialization, not a gate. **No approval.** |
| `peerslate-database-schema` | The only approval in the pipeline (check id 11). |

Azure Pipelines evaluates the checks of **every environment a stage
references** before that stage starts, and it reads those references from the
stage's static text. A job condition that skips the job does not remove its
environment from the evaluation. Microsoft states the rule directly: "Before
the execution of a stage can begin, all checks on all the resources used in
that stage must be satisfied."

So every routine deploy was dragged through the database approval, even when it
had no database work to do.

### Live evidence, not inference

Run **711** was `batchedCI`, `schemaAction=none`, `forceProductionDeploy=false`.
`GovernedSchemaMigration` was skipped by its own condition. The run still parked
at the `peerslate-database-schema` approval and shipped nothing until a person
tapped it. Three earlier runs (669, 683, 653, 707) had queued behind the same
gate, each a redeploy of code that was already live.

The configuration above was read from the live Azure environment with
`az devops invoke --area pipelineschecks --resource configurations`, using
`--api-version 6.0-preview`. The Azure CLI cannot parse `7.1-preview.1`
(`could not convert string to float: '7.1.1'`), which is a large part of why
this stayed invisible for so long.

Build **438** (2026-08-04) is the counter-example that confirms the mechanism:
it was a manual run whose `ProductionOperation` **stage condition** evaluated
false, and it did not park at the approval. A stage skipped by its condition
never reaches the checks phase; a job skipped by its condition does not spare
its stage. That asymmetry is the entire defect, and the entire fix.

## The fix: three stages

| Stage | `dependsOn` | Environments referenced | Asks a human? |
|---|---|---|---|
| `ProductionWebDeploy` | `Build` | `$(environmentName)` only | No |
| `SchemaReadOnlyPreflight` | `ProductionWebDeploy` | **none, deliberately** | No |
| `SchemaApply` | `SchemaReadOnlyPreflight` | `peerslate-database-schema`, and `$(environmentName)` for the lock | Yes — the schema approval |

Job contents are unchanged. Only stage membership, the stage-level `dependsOn`
and `condition`, and the two now-cross-stage job `dependsOn` entries (which had
to be removed, because a job may only depend on jobs in its own stage) differ.

**Why the preflight stage names no environment.** Its connected step
authenticates through a service connection, which carries no checks. That is
what puts the read-only plan on the screen *before* the approval is requested,
rather than after it — closing the recorded scoped finding
`pipeline_schema_checkpoint_order`. Adding an `environment:` to that stage would
silently reinstate the defect, so a test asserts the absence.

Stage conditions: the web stage keeps the previous admission rule verbatim, and
each schema stage is that same rule with `schemaAction != none` added as a
conjunct. `schemaAction` still appears inside the web stage's `or(...)`, which
admits a schema-only run to the request validator; it is never a requirement
for deploying. A test compares all three conditions as exact strings.

Behaviour across every scenario, derived from the shipped conditions:

| Scenario | Web deploy | Preflight | Schema apply | Asks a human |
|---|---|---|---|---|
| Merge to `main` (`batchedCI`) | runs | skipped | skipped | **no** |
| Manual, no force, no schema | skipped | skipped | skipped | no (run is downgraded to `succeededWithIssues`) |
| Manual break-glass deploy | runs | skipped | skipped | **no** |
| Manual schema report/apply/rollback | validates only | runs | runs | yes |
| Task branch, schema apply | skipped | skipped | skipped | no |
| Scheduled maintenance | skipped | skipped | skipped | no |

## The serialization decision

The old single stage serialized web deploys against schema operations across
runs, and `PS-OPS-001/GOVERNED_SCHEMA_MIGRATION_PATH.md` stated that property in
writing. Splitting it would have lost that property silently — the document
would simply have become untrue.

**Chosen: pure YAML.** `SchemaApply` contains a second deployment job,
`HoldSharedProductionReservation`, that targets `$(environmentName)` and does
nothing else — no package, no database command, no CLI task. A stage takes an
environment's exclusive lock only if the stage references that environment, so
this reference restores the property with no configuration change and no new
human gate. It is reversible by reverting the same commit.

**Rejected: adding an exclusive lock check to `peerslate-database-schema`.**
Semantically cleaner, but it is an environment configuration change, which this
package does not make.

`lockBehavior: sequential` is set on both lock-holding stages and is
load-bearing, not decorative: the documented default is `runLatest`, which would
cancel a queued run in favour of a later one. Schema is not a cumulative
artifact, so a discarded run is a lost operation.

Two honest limits on what the restored property means:

- Azure evaluates the exclusive lock in category 5, **after** approvals in
  category 3. A schema run waiting on its approval therefore does not hold the
  production lock, and a merge landing during that wait deploys normally.
  Serialization covers the execution window. This is strictly better than the
  old behaviour, where the deploy was behind the approval itself, but it is not
  the same claim, so the governance document now says so.
- `HoldSharedProductionReservation` leaves a deployment record against the
  `peerslate-pete` environment. Read that environment's history by stage name;
  not every entry shipped code.

## The schema approval remains human-only, by intent

**The approval on `peerslate-database-schema` (check id 11) is untouched by this
package.** It was not weakened, bypassed, shortened, or moved. Every schema
`report`, `apply`, and `rollback` still stops and waits for a person. That is
deliberate: the goal of this work is "routine web deploys ask nobody", and it
was never "fewer gates on database work".

A machine-wide permission bypass — anything that let an agent approve that
environment, or that granted a session standing authority to release it — would
make the sentence above untrue in practice while leaving it true on paper. Such
a bypass is **not required by this package, not authorized by it, and not part
of it.** Nothing here depends on one. If a future change makes that statement
false, this document must be corrected in the same change.

Related recorded finding, still open and unchanged: `schema_environment_approver_identity`
records that the approver and the person queueing the run are the same human, so
this is a deliberate pause rather than separation of duties. Describe it that
way and nothing stronger.

## Verification

Automated, in this branch:

- `tests/test_operational_readiness.py` — the stage list, the exact-literal
  environment names, the three exact stage conditions, the ordering chain, the
  preflight stage's absence of any `environment:`, and the reservation job's
  inertness.
- `tests/test_schema_migration_path.py`, `tests/test_community_revival.py` —
  corrected to the new stage names, with the Build-stage bound made
  self-checking so a future rename fails loudly instead of silently widening.
- Six mutations that reintroduce the defect (schema environment added to the
  web stage; `environment:` added to the preflight stage; reservation job
  deleted; `lockBehavior` dropped; a `schemaAction` requirement added to the web
  stage's condition; the reservation job turned into a real deploy) were each
  confirmed to fail the suite.

Still required on a real run, and not yet evidence:

1. A real merge to `main` deploys end to end with no human interaction.
2. A `schemaAction=none` run shows both schema stages skipped in the timeline.
3. A `schemaAction=report` run does request the approval, and its read-only plan
   prints before the approval is requested.
4. The post-deploy smoke fails loudly rather than degrading silently.
5. A one-command rollback to the previous known-good SHA is rehearsed.
6. Check id 11 is re-read at closeout and recorded as present and unchanged.

**Rollback:** revert the single pipeline commit. No environment configuration
was changed, so there is nothing else to undo.

## Preserved deliberately

The exact-source post-deploy smoke and its 420-second warmup; the overlap and
duplicate-run refusals in `scripts/production_operation_preflight.py`, including
the message that names the competing run id; the Candidate deploy/smoke/stop
stages; the scheduled Community maintenance isolation; and every fail-closed
condition. This is a restructuring, not a relaxation.

`manualProductionSourceVersion` and `forceProductionDeploy` are kept but are now
break-glass rather than routine: with automatic deploys no longer parking, the
manual fallback should be rare.

## Known stale references, out of this package's surfaces

These name the removed `ProductionOperation` stage and should be corrected by
whoever owns them:

- `scripts/govern_sql_migrations.py` (module docstring)
- `docs/initiatives/PS-OPS-001/README.md` (two references)

Historical records in `PS-DELIVERY-RESET-001` also name it; those describe what
was true when written and are left alone as evidence.

## Deferred, deliberately not smuggled in

Having a run self-skip production when its source version is no longer the tip
of `main` would have prevented tonight's stale queue. It changes deploy
semantics, so it belongs to a separate owner-decided slice.

## Gotcha: branch-policy path filters need a leading slash

The risky-path reviewer policy was created with paths like `identity.py` and
`docs/governance/*`. Azure DevOps accepted them without complaint, stored them
verbatim, and reported the policy as enabled and blocking — but it matched
**nothing**. Path filters must be repository-root-relative and begin with `/`:
`/identity.py`, `/docs/governance/*`, `/SQL FIles/*`.

This is a silent failure: the policy list shows a healthy, blocking, enabled
rule while it guards zero files. It was caught only by opening a pull request
that touched two guarded paths and noticing no reviewer was attached.

Two consequences worth keeping:
- If this policy is ever recreated, verify it by opening a PR that touches a
  guarded path and confirming a required reviewer is actually attached.
  Do not trust the policy list alone.
- Automatically-included reviewers are attached when a pull request is
  **created**. Fixing the policy does not retroactively add reviewers to pull
  requests that already exist; the corrected rule applies from the next PR.
