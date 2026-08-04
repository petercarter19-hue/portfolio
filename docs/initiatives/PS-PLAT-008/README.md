# PS-PLAT-008 — Production migration state is verified, not assumed

## Package status

- Status: **Planned — not active**
- Origin: discovered 2026-08-04 during the Community public-pilot release
- Designated session manager: Unassigned
- Implementation writer: Unassigned
- Base: `origin/main` at `3f8a6e7e215424a7aa239da59f3a799b1ba727cf`
- Migration owner: this package authorizes **no new migration**; see "Why there
  is no SQL here"
- Visual authority: none; no user-facing surface
- Release boundary: operational verification only

## The problem, stated accurately

On 2026-08-04 the Community migrations were applied to production. The
verification that runs afterwards failed three checks:

```text
FAILED: Migration ledger is missing required foundation records: PS-PLAT-000.
FAILED: Not every application user has exactly one member profile.
FAILED: One or more members do not have discovery disabled by default.
```

Re-running the foundation set with `--apply` cleared **all three**, and both
verifications then passed.

That outcome is the finding. Nothing was wrong with the repository: the
`member_profiles` and `connection_preferences` rows are seeded by
`dbo.usp_UpsertAppUserFromAuth`, and that seeding has been present since
PS-AUTH-001 was first written on 2026-07-17 (`ca24d1f`, PR 50). The backfills in
PS-PLAT-002 and PS-PLAT-004 are idempotent and corrective.

**Production had drifted behind the repository's migrations, and nothing
detected it.** The ledger was missing an entry, procedures and backfills were
behind, and the only reason it surfaced is that a feature happened to need a
migration and someone happened to run the verifier. Had the Community package
not required schema work, the drift would still be invisible.

### A correction worth recording

The first analysis of this incident concluded that "no application code creates
either row," based on searching `*.py` files. The rows are created by a stored
procedure — SQL, not Python — so the search could not have found it, and the
conclusion was wrong. It also produced a wrong prediction: that re-applying the
foundation set would fix only the ledger entry and leave the two data findings
standing. It fixed all three. Recorded here because the wrong diagnosis would
have produced a package that seeded rows already being seeded.

## Why there is no SQL here

The corrective SQL already exists and already works. `--apply` re-runs the
foundation set idempotently, and run 475 of the disposable SQL proof
demonstrates that re-application is safe: every foundation migration plus the
three Community migrations were applied twice against a real SQL Server 2022
with no error.

Adding a migration to fix data that a re-apply already fixes would be
ceremony. The gap is detection, not repair.

## Scope

Make production's applied migration state observable, so drift is noticed when
it happens rather than years later by accident.

In scope:

- A routine check that production's `schema_migrations` ledger contains every
  migration the repository expects.
- A clear, loud report when it does not.
- Documented remediation: re-apply the foundation set, which is proven safe.

Out of scope:

- New tables, columns, or backfills.
- Changing `usp_UpsertAppUserFromAuth`; it is correct.
- Auto-applying migrations from the deployment pipeline. The runbook forbids
  it, and it would remove the human review the current flow requires.

## Implementation options, for the manager to choose

The choice turns on where a database connection may live, which is an owner
decision rather than a writer's.

**Option A — application-side readiness surface.** The app already holds a
database connection. Expose the recorded ledger through an owner-only
diagnostic and compare it against the expected list. No new secret anywhere.
Weakest coupling to the pipeline; requires the app to be running.

**Option B — pipeline verification stage.** Run `verify_foundation` against
production after each deploy. Loud and automatic, but requires a production SQL
connection string as a pipeline secret, which today does not exist and is a
meaningful expansion of what the pipeline can reach.

**Option C — scheduled operator run.** A documented cadence for running
`--verify` manually, recorded in the ops runbook. No new surface and no new
secret; relies on a person remembering, which is exactly what failed here.

Recommended: **Option A**, because it adds no secret, and because the drift it
detects is a property of the running system rather than of a deployment event.

## Acceptance evidence

- The check reports a missing ledger entry when one is missing, proven by
  removing one in a disposable database rather than by assertion.
- The check is quiet and cheap when state is correct.
- No production credential is added to the pipeline unless Option B is chosen
  explicitly by the owner.
- The runbook records the remediation and states that re-applying the
  foundation set is proven idempotent, citing proof run 475.

## Related

- `docs/initiatives/PS-COMMUNITY-PUBLIC-PILOT-001/PRODUCTION_MIGRATION_2026-08-04.md`
  — the incident record, including the corrected analysis.
- `docs/AZURE_DEVOPS_DEPLOYMENT_RUNBOOK.md` — the approved migration flow.
- `scripts/apply_sql_migrations.py` — `verify_foundation` and the expected
  migration list.
