# PS-MYOPP-CANONICAL-001 — C2 canonical shared-side foundation

This Protected child implements the accepted REC-02 fixture-only C2 boundary:
provider-neutral connector contracts, deny-by-default versioned source-policy
enforcement, immutable receipts and source/requirement versions, source and
application-link lifecycles, canonical dedupe/merge/split, governing-source
failover, attribution, rights-bounded tombstones, the six-condition Live
Opportunity Gate, and reusable safe-outbound validation.

The source is deliberately shared-side only. It has no route, scheduler,
provider credentials, external request transport, member table, member key, or
member-side join. The in-memory repository and synthetic connector support P-1
fixtures only; they do not claim provider, schema-apply, deployment,
enablement, or live-opportunity behavior.

The additive `PS-MYOPP-001` migration creates only distinct `dbo.myopp_*`
objects. Its registry gate is intentionally `null`: C2 has no authority to
provision, spend on, or operate an external Azure SQL gate database. Its next
schema action is an owner-authorized disposable P-2 gate, followed separately
by independent review, PR, merge, and any governed schema operation.
