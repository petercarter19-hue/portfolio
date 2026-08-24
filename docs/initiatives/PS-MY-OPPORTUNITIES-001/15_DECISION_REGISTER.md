# 15 — Decision register

Four strictly separated categories. Category B was authored as
recommendations and was **resolved at the 2026-08-24 architecture
acceptance** (§2); no `decision_pending` item remains anywhere in this
register. Status vocabulary: `accepted` (owner or owner-delegated),
`decision_pending` (historical: recommended, then awaiting Pete — now an
empty state), `deferred` (safe, gated — §3), `blocker` (none exist).

## 1. Owner decisions already made (category A — recorded, binding)

| Decision | Record |
|---|---|
| P0 activation, constitutional/route interpretation, documentation-only through-merge boundary, withheld authorities | `docs/governance/DECISIONS.md` 2026-08-23 entry; claim `owner_outcome_ref` |
| Two destinations (My Opportunities, Opportunity Slate); no For You; Saved is a relationship/view | R3 decision ledger (accepted) |
| Visible interpreted draft before explicit Apply; focused clarification, nothing preselected; post-result refinement leaves current results unchanged until a new Apply | R3-4 (accepted; carried into docs 03/04) |
| Strict `Fully verified` gate; four canonical assessment states; missing evidence is never negative | R3 + preserved V2/V4 (accepted; doc 07) |
| Preferred orders after the gate; Practical fit separate; no score/probability/prediction/paid relevance | R3 (accepted) |
| Exactly two search/control rows at every supported viewport | R3-3 (accepted; geometry artifacts pending, §2) |
| Copy truths: `Review in Opportunity Slate`; `customer and business outcomes at scale` | R3 (accepted corrections) |
| Save ≠ apply ≠ Slate ≠ monitoring; explicit Slate confirmation | R3 (accepted) |
| Server-derived identity; authorization before retrieval/AI; AI proposes, people decide | Constitution/Site Rules (standing) |
| Journal dormant; Profile not live evidence truth without verified cutover | R3 (accepted) |
| No scraping of LinkedIn/Glassdoor/Indeed-class services; API access ≠ rights | Preserved V2 (rejected directions) |
| First credible live private-sector release requires ≥1 owner-approved licensed commercial feed | R3 (accepted release gate) |
| Warm editorial visual character; near-black role titles; true mobile reflow | R3/V4 (accepted) |
| Program manager: Codex session `01a02f42-15ac-7d92-a2a9-60b7e800c388` | Pete's selection (R3-1) |
| Architecture acceptance of the merged P0 (`09262ea8…`): REC-01–REC-08 dispositions in §2 and the doc 14 child graph as written | Owner-delegated Codex PM decision adopted by Pete; `18_ARCHITECTURE_ACCEPTANCE.md`; `DECISIONS.md` 2026-08-24 entry |

## 2. Architecture recommendations (category B — **resolved at architecture acceptance, 2026-08-24**)

All eight recommendations were resolved by owner-delegated program-manager
decision adopted by Pete, binding to the P0 architecture merged as
`09262ea819f4a9a643a142a7a28a704de3fc839f`. None is `decision_pending` any
longer. The full acceptance record, with every qualification, is
`18_ARCHITECTURE_ACCEPTANCE.md`.

| ID | Disposition |
|---|---|
| REC-01 | **accepted with the conservative dependency** — v2 lineage; v1 configuration rollback only; option (a): `C7` waits for a meaningful review-capable v2 workflow and resolution of the current intake/workbench breakage; no interim stage-two handoff; re-verify the real production flag and capability state at `C7` activation |
| REC-02 | **accepted as recommended** — Azure SQL canonical truth; Azure AI Search only a rebuildable shared discovery projection; canonical truth outside the index, local fencing, truthful SQL fallback. Architecture selection only: asserts no existing capacity and grants no spending, provisioning, configuration, migration, schema, deployment, or enablement authority; those return for separate approval before any external commitment. Recorded before `C2` activates |
| REC-03 | **accepted** — system re-verification re-admits to the general pool; each member's saved/result/Slate context stays `posting_changed` until that member reviews; new `requirement_version` only on material normalized-clause difference |
| REC-04 | **accepted** — consistent route registration with per-request `before_request` flag gating. Does not turn the flag on |
| REC-05 | **accepted** — member data never enters the shared discovery index |
| REC-06 | **accepted** — ambiguous required/preferred defaults to required and is visibly flagged; may withhold `Fully verified`, never overclaims it |
| REC-07 | **accepted** — `Last checked` is the last successful verification and its age; failed attempts shown separately; copy matches the real execution path and is contract-tested |
| REC-08 | **architecture accepted; enablement deferred** — the isolated `C13` design is the only permitted shape. `C13` stays inactive, disabled, and unauthorized; permitted source classes and retention rights remain later owner decisions; `C10` paste/upload remains unconditional |

The recommendation rationale, evidence, and rejected alternatives below are
retained solely as **pre-decision history** — the durable record, as written
before the 2026-08-24 acceptance, of how each disposition was reached.
Nothing in the table below is a current open choice or a pending owner
selection; where its wording reads as pending, the dispositions table above
and `18_ARCHITECTURE_ACCEPTANCE.md` control.

| ID | Recommendation | Evidence | Alternatives considered |
|---|---|---|---|
| REC-01 | *Pre-acceptance recommendation:* C7 targets the v2 Slate lineage; v1 is rollback-only; C7's capability dependency was proposed for resolution as doc 11 §3 option (a) or (b). *The 2026-08-24 acceptance selected option (a) — the conservative dependency (§2 above)* | Doc 11 §1 (route conditional, production flag evidence, applied schema, current service idioms) | Target v1 (couples to the surface being replaced); defer C7 entirely (weakens the product promise; Slate routing is a core approved action) |
| REC-02 | *Pre-acceptance recommendation:* Azure SQL canonical truth + rebuildable discovery-index candidate (Azure AI Search) with canonical-outside-index + local-fence patterns — at candidate time recommended and not yet selected (the frozen R3 ledger then held final canonical-store/search-index topology open and named neither store as selected). **Timing/gate:** P0 and C1 are decision-free (logical contracts and documentation only); the gate required the REC-02 decision to be durably recorded **before C2 activates** — before any physical store selection, schema, migration, projection, or provider-dependent design anywhere in the program (doc 14 §1; doc 02 §6; doc 13 §3). *The 2026-08-24 acceptance recorded that decision (§2 above): Azure SQL is canonical truth and Azure AI Search is only a rebuildable projection — architecture selection only, with no capacity, spend, provisioning, topology-provisioning, credential, migration, provider-contract, or production authority; the before-C2 gate is thereby satisfied when C2 later activates* | Owner ledger working direction; Search 3F committed patterns; doc 04 §§9–10 degraded modes make either outcome safe | SQL-only retrieval (simpler, weaker ordering/scale headroom); index-primary (rejected: canonical truth must not live in a rebuildable projection) |
| REC-03 | Changed-posting re-admission: system re-verification re-admits to the general current pool under the then-governing requirement version (a **new** `requirement_version` only when the normalized clauses materially differ, doc 03 §10); each member's saved/result/Slate contexts stay `posting_changed` until that member reviews | Approved posting-changed state + R2 carried note ("who re-admits"); doc 03 §2 | Member-review-gates-everything (one member's inaction would hide a live role from everyone); system-clears-everything (silently rewrites member context) |
| REC-04 | All new My Opportunities routes: register-always + blueprint `before_request` flag gate (ask-pete-direct style) | `app.py:810-816` documented rationale; sign-in report's per-test limitation of the registration-conditional style | Registration-time conditional (the existing Slate compromise; poorer testability, restart-coupled) |
| REC-05 | Member data never enters the shared discovery index; assessments/saves/criteria live only in owner-scoped canonical storage | Doc 02 invariant 4; doc 08; Search 3F public-projection discipline | Per-member index documents (rejected: revocation/deletion cleanup risk and cross-member blast radius for zero product need) |
| REC-06 | Ambiguous required/preferred classification defaults to `required` for gate purposes, flagged member-visible | Doc 07 §2; conservative direction can only withhold `Fully verified`, never overclaim | Default preferred (risks overclaiming the gate); per-case AI judgment (unauditable) |
| REC-07 | `Last checked` binds to *last successful verification* with its age; failed attempts render separately ("could not reach the source `<attempt age>`"); loading copy is selected by the accepted topology at C4 (index wording vs live-check wording) and asserted by copy tests | R2-REV-007; doc 02 invariant 3; doc 16 rows | Single ambiguous timestamp (the defect the review flagged); always-live-check wording (untruthful under index topology) |
| REC-08 | If Pete ever enables member-URL fetch for My Opportunities, it is delivered as the distinct future child C13 (`PS-MYOPP-URL-FETCH-001`, doc 14) — a **service-only late integration** through C10's prebuilt disabled port and C2's `safe_outbound` validator, gated by the proposed `PEERSLATE_MY_OPPORTUNITIES_URL_FETCH_ENABLED` alongside the parent surface flag, reopening no closed ownership — implementing doc 06 §§1–4 exactly, landing only in the owner-scoped `member_import` path (docs 02/06), never entering the shared supply pipeline, and staying separate from the Slate's existing link intake | Doc 06; Site Rules §3; continuation extraction direction; doc 02 invariant 8 | Reusing Slate import as-is (couples to an unresolved breakage boundary and different product semantics); shared-connector treatment (rejected: would make private material inventory); folding fetch into C10 (rejected: C10 closes after paste/upload — a closed claim cannot resume); C13 reserving closed route/app/template surfaces (rejected: recreates hot-file collisions the port design avoids) |

## 3. Safe deferrals (category C — each named with its gate; none blocks P0 review)

| Deferral | Gate that will require it |
|---|---|
| Exact licensed feed provider + contract + full rights values | C11 activation (`PS-MYOPP-LICENSED-FEED-ADAPTER-001`); C11 completes before any C9 Level 3 licensed-feed operation (C1 prepares; Pete decides) |
| Provider spending or paid service | External commitment |
| Evidence strength + corroboration policy values | Qualification implementation/release (C5) |
| Freshness + closure-decision thresholds | Live Opportunity Gate activation (C9) |
| Company-information/sentiment providers + permissible claims | C12 activation (`PS-MYOPP-COMPANY-CONTEXT-001`); C12 completes before any live company-context claim (C1 prepares; the truthful absent state ships without it) |
| Whether member-URL fetch is enabled at all; permitted source classes; retention rights | C13 activation (`PS-MYOPP-URL-FETCH-001`, a distinct future claim after C10 closes; paste/upload in C10 is unconditional) |
| Known-unmet-role treatment in broader views — ordering, labeling, or filtering by unmet count (the current doc 04 §4 broader chain is deliberately owner-neutral and uses **no** preferred-count or unmet-count signal) | Broader-result implementation/release; Pete's accepted treatment may then explicitly amend the doc 04 §4 broader chain |
| Corrected desktop/iPad two-row artifacts (Original ChatGPT → Pete lock) | Material UI implementation (C8) — quarantine per R3-3 |
| Real-build visual parity disposition | C8 merge/release |
| Exact async job/queue technology; budget values | C9 operations design |
| Migration/cutover/rollback execution + first credible release boundary | Production migration / live completion claim (C9) |
| Opportunity-change monitoring/notifications; Community/feed placement; standalone company destination; broader company-risk intelligence | Separate future owner-approved packages, if ever (preserved V2 deferrals) |
| Member retention window for result snapshots | C4 (the executions/results persistence owner, doc 02 §6) |
| Evidence-source port binding | C5 activation (doc 07 §6; escalates only if no truthful source exists then) |

## 4. Blockers (category D)

**None.** No ownership, privacy, authorization, rights, constitutional,
material-visual, migration, or repository conflict prevents the independent
architecture review of this candidate. The visual-geometry quarantine and all
§3 rows are safe deferrals with named gates, not blockers (per the trial
contract's verdict rules).

## 5. Where each pending decision lands

**Resolved 2026-08-24.** REC-01 through REC-08 and the child graph (doc 14)
were accepted by owner-delegated program-manager decision adopted by Pete, and
are recorded in `18_ARCHITECTURE_ACCEPTANCE.md` and the `DECISIONS.md`
2026-08-24 entry. Doc 14 is accepted exactly as written and is unchanged by
that acceptance. Acceptance activates no child. Everything in §3 remains open
and is raised only when its dependency becomes real, per the program model.
