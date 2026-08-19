# Search 3F V3 — Independent Review Checklist

## Reviewer authority

Review the exact pushed candidate SHA read-only. Fetch `origin`, read the
candidate diff from its recorded base, read this package and the historical
handoff evidence, and refresh standing Azure state with read-only calls if it
is still available. Do not modify Git, Azure, iCloud, or handoff files; do not
rerun the historical proof battery; do not execute teardown.

Return severity-ranked findings, explicit answers to all sixteen questions,
one verdict (`Pass`, `Conditional`, or `Fail`), and one retain-versus-teardown
recommendation. A Conditional verdict must name the finite changes required
for Pass. Name anything not verified rather than waiving it.

## Architecture and repository questions

1. Does every shared-service statement distinguish scoped proof permissions
   from service isolation, inherited readers, administrators, and key holders?
2. Is a dedicated service still named as the recommendation when actual
   service-level isolation is required, without claiming it removes all
   subscription, management-group, tenant, or human authority?
3. Do the exact schema, query select, fence, and seven-field serializer prevent
   backend-field return while honestly recording all 20 fields as stored and
   retrievable?
4. Does the local fence validate the complete canonical publication record,
   and is it clearly not presented as a deployed API or member relationship
   boundary?
5. Are lexical pins, audience/schema filter, explicit select, bounded adaptive
   paging, unique tie-break, and deterministic local ordering complete and
   enforced rather than merely described?
6. Are all latency/deletion statements labelled as small historical
   observations with no vendor guarantee or invented percentile?
7. Is cleanup complete, exact-target, fixed-date, idempotent, available after
   expiry, and unable to treat an authorization/network/CLI failure as proof
   that a target is absent?
8. Are cost claims limited to historically unchanged capacity, with usage
   dollars and per-index attribution explicitly not assessed?
9. Was registration/activation performed from authoritative `origin/main`
   through the required lane process, and is this candidate still unmerged,
   undeployed, and not member-visible?
10. Does the finite V3 decision/test inventory supersede the contradictory V2
    namespaces without erasing the historical record or carrying an undeclared
    open decision?

## Execution and evidence questions

11. Does every historical evidence file support only the claim made from it,
    especially API pin, request census, Ask Pete counters/digest, restore,
    determinism, and the historical 18/18 and 25/25 labels?
12. If Azure is inspected, does current standing state match the recorded
    index, fixture, role, identity, service-capacity, and Ask Pete boundaries
    exactly, with any drift or extra grant reported?
13. Are V3 test names and assertions as strong as their claims, including body
    census, 50-repeat order, all-field fence mutation, local-only serialization,
    persistent budgets, zero-network defaults, and teardown preflight?
14. Are residual exposures and exclusions complete and correctly classified,
    including publisher read capability, sole-operator history, shared readers,
    key posture, CMK, semantic service setting, missing Ask Pete digest proof,
    missing restore evidence, and no deployed member authorization?
15. Should the retained proof resources remain standing beyond the existing
    expiry, or be torn down at 2026-08-23 23:59 CDT? Give one deciding factor;
    do not infer an extension.
16. Is the exact candidate fit to land unchanged as a non-production
    architecture/operator-tooling package, while leaving merge, deployment,
    teardown, Gate L2, and member-facing Search to separate authority?

## Required evidence in the return

Record the fetched `origin/main` SHA, reviewed candidate SHA, timestamps,
commands/tests used, current Azure inspection time if applicable, any files or
state unavailable, and whether the proof-only scripts are absent from the
deployment ZIP selection. The writer-authored matrix is a navigation aid, not
the review verdict.
