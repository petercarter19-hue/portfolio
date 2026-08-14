# PS-REPOSITORY-RATIONALIZATION-001 - Package and evidence rationalization

**Status:** Completed and merged through Azure review. Implementation main
`eea1293a80091b8f19229a47782b5c2222e7ec32` was automatically deployed by run
1027; live health returned 200 at release `8f30f3770dc1d8a6a440da94`. The change
contained no application-runtime source or intended product behavior change.
The exact current lifecycle state belongs to `CURRENT_LANES.json`.

## Outcome

Make the repository easier to understand and cheaper to maintain without
discarding authority or history:

- account for every initiative directory in one non-authoritative package
  registry;
- correct eight known stale or mixed package status headers;
- establish one retention and exact-deduplication standard;
- retain canonical Opportunity Slate and Community authority while removing
  only verified secondary copies; and
- add a deterministic check that rejects new unapproved large exact
  duplicates.

## Authority boundary

`CURRENT_LANES.json` and `CURRENT_BASELINE.yaml` continue to control delivery
and lifecycle state. The registry is a rationalization index; it does not
activate, release, retire, or prove a package live.

The rationalization changed no application-runtime source, route, schema,
migration, configuration, dependency, pipeline, production data, or intended
product behavior. Its implementation merge nevertheless triggered the normal
main pipeline and production deployment. `artifacts/` is excluded from the
deployment package, while `docs/` is included because the live Control Room
has runtime readers. Runtime and dormant-asset retirement remains a separate
Gate Retire decision.

## Retention boundary

No unique evidence, accepted visual authority, release or incident proof,
migration record, legal/privacy/security evidence, sealed handoff, dirty
workspace content, stash, branch, recovery ref, or member-authored data may be
removed here.

The exact deletion set is limited to:

- 25 OS-4 files under `artifacts/2026-08-04-os4/signed-in/` whose bytes are
  retained under `PS-OPPORTUNITY-SLATE-001/evidence/os-4/`;
- all six public-pilot candidate PNG copies whose bytes are retained in Pete's
  accepted Community authority; and
- four completion-candidate PNG copies whose bytes are retained in that same
  accepted authority, while the two unique completion candidates remain.

Every removal receives a repository-relative canonical pointer and exact hash
record. Full completion evidence is recorded in `COMPLETION_REPORT.md`.
