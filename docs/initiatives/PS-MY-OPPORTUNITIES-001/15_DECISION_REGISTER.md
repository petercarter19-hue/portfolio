# 15 — Decision register

Four strictly separated categories. Nothing in category B is treated as
accepted anywhere in this package; each names its evidence and alternatives.
Status vocabulary: `accepted` (owner), `decision_pending` (recommended,
awaiting Pete), `deferred` (safe, gated), `blocker` (none exist).

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

## 2. Architecture recommendations (category B — `decision_pending` at architecture acceptance)

| ID | Recommendation | Evidence | Alternatives considered |
|---|---|---|---|
| REC-01 | C7 targets the v2 Slate lineage; v1 is rollback-only; C7's capability dependency resolved as doc 11 §3 (a) or (b) | Doc 11 §1 (route conditional, production flag evidence, applied schema, current service idioms) | Target v1 (couples to the surface being replaced); defer C7 entirely (weakens the product promise; Slate routing is a core approved action) |
| REC-02 | Topology recommendation: Azure SQL canonical truth + rebuildable discovery-index candidate (Azure AI Search) with canonical-outside-index + local-fence patterns — **recommended, not selected** (the frozen R3 ledger holds final canonical-store/search-index topology open before canonical and retrieval implementation, and names neither store as selected). **Timing/gate:** P0 and C1 are decision-free (logical contracts and documentation only). Pete's REC-02 decision is required **before C2 activates** — before any physical store selection, schema, migration, projection, or provider-dependent design anywhere in the program; every later migration-bearing child inherits the gate (doc 14 §1; doc 02 §6; doc 13 §3) | Owner ledger working direction; Search 3F committed patterns; doc 04 §§9–10 degraded modes make either outcome safe | SQL-only retrieval (simpler, weaker ordering/scale headroom); index-primary (rejected: canonical truth must not live in a rebuildable projection) |
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

Pete's architecture-acceptance turn should resolve: REC-01 through REC-08
(accept/correct each) and the child graph (doc 14). Everything in §3 is
raised only when its dependency becomes real, per the program model.
