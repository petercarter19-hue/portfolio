# PS-PLAT-008 — Production migration state is verified, not assumed

## Package status

- Status: **Superseded before implementation. Closed.**
- Superseded by: the governed schema migration path in `PS-OPS-001`
  (`docs/initiatives/PS-OPS-001/GOVERNED_SCHEMA_MIGRATION_PATH.md`)
- Opened and closed: 2026-08-04

## Why this existed

On 2026-08-04 the Community migrations were applied to production and the
foundation verification failed three checks. Re-applying the foundation set
cleared all three. The finding was not any of the three failures: it was that
**production had drifted behind the repository's migrations and nothing
detected it.** The drift surfaced only because a feature happened to need a
migration and someone happened to run the verifier.

This package proposed the smallest thing that would make drift observable: a
read-only ledger procedure and an owner-only Control Room endpoint comparing it
against the list the repository expects.

## Why it is closed without shipping

While it was being implemented, the governed schema migration path landed on
`main` from the PS-OPS-001 lane. It addresses the same problem more completely:

- it computes what is pending by **reading `dbo.schema_migrations` live**,
  rather than trusting a filename list to match reality;
- it records the result in `docs/governance/PRODUCTION_SCHEMA_STATE.md`, so the
  repository can state what production carries;
- it refuses any migration not proven against a throwaway database; and
- it runs from the pipeline's `SchemaMigration` stage rather than from an agent
  connected to production with a credential.

That last point matters most. This package's own root-cause incident included an
agent applying schema to production by hand — and the governed path removes that
route entirely rather than adding a light on top of it.

Shipping this package's endpoint alongside it would have created a second
mechanism reporting the same fact from a different source, which is precisely
the competing-truth-store failure `AGENTS.md` forbids: *"Keep one authoritative
source for each fact and derive projections from it."*

The implemented code — one read-only procedure, a comparison service, and an
owner-only endpoint — was removed before merge rather than left dormant.

## What carries forward

Nothing in code. The incident record stays where it is useful:

- `docs/initiatives/PS-COMMUNITY-PUBLIC-PILOT-001/PRODUCTION_MIGRATION_2026-08-04.md`
  — what happened, including the corrected root-cause analysis.
- Proof run 475 — evidence that re-applying the foundation set is idempotent
  against a real SQL Server, which is the remediation the governed path will
  also rely on.

If the governed path is ever removed or bypassed, the problem this package
described returns, and this document is the record of what it looked like.
