# 18 — Architecture acceptance

Owner-delegated acceptance of the `PS-MY-OPPORTUNITIES-001` P0 architecture.
This document records decisions; it authorizes no implementation.

## Status and binding

| Field | Value |
|---|---|
| Accepts | The P0 architecture merged to `main` as `09262ea819f4a9a643a142a7a28a704de3fc839f` |
| Reviewed candidate | `e040677f69b0fabf4ca97998dfcc867f1b55eec3` (independent pass, zero findings) |
| Acceptance package | `PS-MY-OPPORTUNITIES-ARCHITECTURE-ACCEPTANCE-001`, Protected, documentation only |
| Decision provenance | Owner-delegated **Codex program-manager selections**, adopted by Pete |
| Authorizes | Recording these decisions in the repository, through independently reviewed merge |
| Does **not** authorize | Any implementation child, provider contact/selection, purchasing, spending, provisioning, schema, migration, runtime code, infrastructure, visual creation, deployment, enablement, cutover, or production action |

### How these decisions were made

Pete directed the Codex program manager
(`session:01a02f42-15ac-7d92-a2a9-60b7e800c388`): *"I trust your decision
making, so please give me a handoff to answer all these and move forward the
best way with this package with Claude."* The dispositions below are therefore
**program-manager selections made under an explicit owner delegation**, adopted
by Pete as binding. They are not a claim that Pete personally authored each
technical clause. Where a decision reserves a later owner act — provider
choice, spending, enablement, visual authority — that act remains Pete's and is
untouched by this acceptance.

## Architecture decisions

### REC-01 — Slate target: **accepted with the conservative dependency**

Target the Opportunity Slate **v2** lineage. v1 remains configuration rollback
only.

Dependency **option (a)** is selected: `C7` waits until v2 provides a
meaningful review-capable workflow **and** the current intake/workbench
breakage is resolved. The interim stage-two handoff must not be used. The real
production flag and capability state are re-verified when `C7` approaches
activation.

### REC-02 — Topology: **accepted as recommended**

Azure SQL is canonical truth. Azure AI Search is **only** a rebuildable shared
discovery projection. Canonical truth stays outside the index; local fencing
applies; a truthful SQL fallback is required.

This is **architecture selection only**. It asserts nothing about existing
capacity, provisioning, or cost, and grants no spending, provisioning,
configuration, migration, schema, deployment, or enablement authority. Those
facts are verified and returned for separate approval before any external
commitment. The gate stands: REC-02 is durably recorded before `C2` activates,
and no child selects a physical store, schema, migration, projection, or
provider-dependent design before it.

### REC-03 — Changed-posting re-admission: **accepted**

After successful system re-verification a changed posting may re-enter the
general current-opportunity pool. Each member's saved, result, and Slate
context remains `posting_changed` until that member reviews it.

A new `requirement_version` is created **only** when normalized requirement
clauses materially differ. Other posting changes preserve truthful
change/history presentation without unnecessary assessment churn.

### REC-04 — Route registration and flag gating: **accepted**

My Opportunities routes register consistently; the feature flag applies through
per-request `before_request` gating. **This decision does not turn the flag
on.**

### REC-05 — Member data isolation: **accepted**

Member data never enters the shared discovery index. Criteria, evidence,
assessments, saves, private imports, and other member records remain
owner-scoped in canonical storage.

### REC-06 — Ambiguous requirement classification: **accepted**

Ambiguous required-versus-preferred wording defaults to **required** for the
`Fully verified` gate, with the ambiguity visibly flagged. This may withhold
`Fully verified`; it must never overclaim it.

### REC-07 — Verification recency truth: **accepted**

`Last checked` means the last **successful** verification and its age. Failed
attempts are shown separately and truthfully. Copy matches the real SQL/index
execution path and is contract-tested.

### REC-08 — Member URL fetch: **architecture accepted; enablement deferred**

The distinct optional `C13` design is accepted as the only shape member URL
fetching may take.

This does **not** decide or imply that URL fetching will be enabled. `C13`
remains inactive, disabled, and unauthorized. Permitted source classes and
retention rights remain later owner decisions. Paste/upload in `C10` remains
unconditional.

## Child graph — accepted as written

The strict one-active-child-at-a-time graph in `14_FINAL_CHILD_GRAPH.md` is
accepted exactly as written; that document is unchanged by this acceptance:

```text
C1 → C2 → C3 → C5 → C4 → C6 → C10 → C7 → C8 → C11 → C12 → C9
```

REC-02 is durably recorded before `C2`. Binding qualifications:

- `C11` remains provider/rights-gated and is mandatory before any Level 3
  licensed-feed operation.
- `C12` and `C13` are genuinely skippable.
- `C9` may proceed after `C8` for Level 1–2 work while provider decisions
  remain pending, using the documented governed pause / `C11`-or-`C12` /
  resume sequence before Level 3.
- `C13` may occupy a later one-active-claim window after `C10` closes **only**
  if separately authorized.
- **Architecture acceptance activates no child.**

## Preserved deferrals — not resolved here

None of the following is silently resolved by this acceptance; each keeps the
gate recorded in `15_DECISION_REGISTER.md` §3:

- provider identity, contracts, licensing, cost, or spending;
- evidence-strength policy;
- freshness and closure thresholds;
- company-context providers;
- URL-fetch enablement, permitted source classes, retention rights;
- treatment of known-unmet roles in broader results;
- async/queue technology and operating budgets;
- migration, cutover, rollback execution, and the release boundary;
- production activation;
- corrected desktop/iPad artwork.

## Visual authority

The accepted **exactly two search/control rows at every supported viewport**
invariant remains binding. The desktop/iPad search-band geometry quarantine
stays in force and is safely deferred until `C8`. Claude must not generate or
materially revise that visual authority: Original ChatGPT creates it and Pete
accepts it.

## Authority explicitly not granted

This acceptance does not activate `C1` or any other child, select or contact a
provider, approve spending or licensing, provision or configure infrastructure,
author schema or migrations, write runtime code, create or revise visual
authority, merge runtime work, deploy, enable, cut over, delete, or make any
live product, provider, or compliance claim. Production authority remains
withheld.

## Next step

After this acceptance package independently passes, merges, and closes, the
next program step is a **separately activated** `C1`
(`PS-MYOPP-SUPPLY-RIGHTS-001`) — documentation only, pre-REC-02-safe, with no
provider contact, selection, or spending.
