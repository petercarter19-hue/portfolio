# PS-MY-OPPORTUNITIES-001 — My Opportunities parent, phase P0 — architecture

**Parent ID:** `PS-MY-OPPORTUNITIES-001`
**Phase:** `P0 — architecture` (part of the parent, not a separate
implementation child)
**Package manager:** Codex task/session
`01a02f42-15ac-7d92-a2a9-60b7e800c388` (Pete's explicit selection, recorded in
the external R3 activation candidate and this package)
**Architecture writer:** Claude Fable 5, session
`bead6626-b340-4586-85d4-7f4002a97cf6` (the claim's `writer_ref`)
**Independent review and merge (complete):** Claude Opus 5 session
`0ce281ff-59fe-4ea3-b661-82d1111d74e1` — the model selected by
`docs/AI_MODEL_AND_ROLE_ROUTING.md`, the exact session bound by the Codex
program manager session `01a02f42-15ac-7d92-a2a9-60b7e800c388` — reviewed
candidate `d3d5fc036585d08f554143fa7d48c40b6852f1f2`, returned one finite
correction pass, passed the corrected candidate
`317d4a60634bb38c59c6d716c8487ce075327cb5` (tail `b5c868f6…`), and — after
Azure PR 605 build 1513 failed solely on package-registry admission, the
governed pause, the separate Routine registry-repair package, the resume,
and the two-merge reconciliation with then-current `origin/main` — returned
a renewed **independent pass with zero findings** on exact candidate
`e040677f69b0fabf4ca97998dfcc867f1b55eec3`. Its receipt/evidence tail was
recorded at branch tip `90d9d0b6e83c78ed7ae750eb91b8ff1ef808c275`, and
Azure PR 605 squash-merged the P0 architecture to `main` as
`09262ea819f4a9a643a142a7a28a704de3fc839f` under normal policy. The merged
receipt is the durable repository record of that review.
**P0 base SHA (historical):** `958727c54832d700f3fd1628381bc5e3b5ce7543`
(`origin/main` at P0 activation)
**P0 branch (historical; preserved for squash-byte proof):**
`work/2026-08-23-my-opportunities-p0-architecture`
**P0 claim:** `docs/governance/lane_claims/PS-MY-OPPORTUNITIES-001.json` —
**closed** with `merged_sha 09262ea819f4a9a643a142a7a28a704de3fc839f`
**Current package (this candidate):**
`PS-MY-OPPORTUNITIES-ARCHITECTURE-ACCEPTANCE-001` — the Protected,
documentation-only acceptance recording on branch
`work/2026-08-24-my-opportunities-architecture-acceptance-001`, activated
from main `f13d0fe6a408e694f7e600b065907463bf39f5f0`, same writer
(`writer_ref session:bead6626-b340-4586-85d4-7f4002a97cf6`),
`review_requirement: independent`, `repository_authority: through_merge`,
`production_authority: withheld`. The acceptance decisions are recorded in
this candidate (docs 15/18 and `DECISIONS.md`), but **this acceptance
package itself still awaits exact-SHA independent review and merge** — it
has no receipt or evidence file yet.
**Owner decision records:** `docs/governance/DECISIONS.md`, entries
`2026-08-23 - Activate My Opportunities P0 architecture as private
member-benefit evidence-building` and `2026-08-24 - Accept the My
Opportunities P0 architecture under owner-delegated program-manager
decisions`

## Authority boundaries

- This phase is documentation only. It changes exactly
  `docs/governance/DECISIONS.md` and `docs/initiatives/PS-MY-OPPORTUNITIES-001/`.
- No runtime, template, CSS, JavaScript, Python application or test, schema,
  migration, infrastructure, configuration, pipeline, route, or visual-asset
  edit. No provider research, contact, selection, licensing, or spending. No
  Azure or production access. No merge-to-runtime, deployment, enablement,
  cutover, deletion, or live claim.
- The independently reviewed P0 documentation PR proceeded through merge
  under the P0 claim (Azure PR 605 → main `09262ea8…`; claim closed). The
  acceptance package's independently reviewed documentation PR may likewise
  proceed through merge under its own claim. Everything beyond repository
  merge — implementation, deployment, enablement, production — is withheld.
- Architecture acceptance never grants runtime implementation. Every
  `C1`–`C13` child requires its own later claim, activation, and review.
- The external R3 package
  (`PeerSlate-My-Opportunities-ARCHITECTURE-ACTIVATION-REVIEW-Candidate-R3-2026-08-23`,
  outside this repository) is the accepted activation contract and evidence.
  Where it and current repository authority differ, current repository
  authority and Pete's explicit approved outcome control.

## Product scope in one paragraph

My Opportunities is evidence-building for private member benefit: it helps a
member discover current opportunities matching what they mean and understand
exactly which stated required qualifications PeerSlate can firmly verify from
evidence the member authorized — without pretending certainty that does not
exist. It remains outside a public job board, recruiter-first marketplace,
public listing index, application product, and paid-relevance system. Licensed
opportunity-feed discovery stays separate from member-uploaded URL/job-
description handling, which Site Rules section 3 governs: a privately uploaded
external job description is never published, indexed, recommended, or converted
into a listing.

## Discovery scope actually performed (read-only, at the base SHA)

- `app.py` (conditional Opportunity Slate registration at lines 806–809; flag
  block near lines 311–333; rate-limit endpoint census near lines 940–988).
- `opportunity_slate_routes.py` (legacy v1 blueprint and full workbench route
  set), `opportunity_slate_v2_routes.py` and
  `services/opportunity_slate_v2_service.py` (v2 R1 stages, identity gate,
  same-origin, headers, versioning), `identity.py` (`get_current_identity`),
  `safe_return.py` usage evidence.
- `docs/initiatives/PS-OPPORTUNITY-SLATE-001/README.md`,
  `PS-OPPORTUNITY-SLATE-002/README.md`,
  `PS-OPPORTUNITY-SLATE-CONTINUATION-001/README.md`,
  `PS-SEARCH-DARK-PROOF-001/README.md`,
  `PS-SIGNIN-MEMBER-ARRIVAL-001/OWNER_TECHNICAL_COMPLETION_REPORT.md`,
  `PS-INTERVIEW-AI-EXTRACT-001/11_DARK_TELEMETRY_INFRASTRUCTURE_EVIDENCE.md`.
- `SQL FIles/Migrations/registry.json` and
  `docs/governance/PRODUCTION_SCHEMA_STATE.md` (migration and applied-state
  conventions; `PS-OPPSLATE-001`–`004` all recorded applied).
- Governance: `CLAUDE.md`, `AGENTS.md`, `START_HERE.md`,
  `CURRENT_BASELINE.yaml`, `CURRENT_LANES.json`, all four claim files,
  `DOCUMENT_CONTROL.md`, Constitution v3.0, Roadmap v3.0,
  `PEERSLATE_SITE_RULES.md`, `AI_WORKFLOW.md`, `AI_MODEL_AND_ROLE_ROUTING.md`,
  `PEERSLATE_OWNER_DELIVERY_GUIDE.md`, `OWNER_VISUAL_INTEGRITY_STANDARD.md`,
  `DECISIONS.md`, `docs/templates/OWNER_TECHNICAL_COMPLETION_REPORT.md`.
- Validators discovered: `tests/test_governance_pointers.py`,
  `tests/test_delivery_preflight.py`, `scripts/delivery_preflight.py`,
  `scripts/check_repository_evidence_policy.py`, `git diff --check`.
- External evidence read in its stated order: the complete R3 root records,
  `PROVENANCE/V4_APPROVED_VISUAL_MANIFEST.json` (by reference),
  `REVIEW_EVIDENCE/CLAUDE_FABLE_5_R2_REVIEW_RETURN.txt`,
  `REPOSITORY_SNAPSHOT/INDEX.md`, and the preserved V4/V3/V2 product,
  visual-contract, and research records under `SOURCE_R1/`.
- Not queried: live production configuration, Azure resources, private user
  data, credentials, provider systems, external sites. Live facts this package
  could not prove from permitted repository evidence are labeled unverified
  where they appear.

## Artifact map

| Doc | Contract output | File |
|---|---|---|
| 01 | 1 — Repository reuse and gap map | `01_REPOSITORY_REUSE_AND_GAP_MAP.md` |
| 02 | 2 — Domain and provenance model | `02_DOMAIN_AND_PROVENANCE_MODEL.md` |
| 03 | 3 — State machines | `03_STATE_MACHINES.md` |
| 04 | 4 — Search contract | `04_SEARCH_CONTRACT.md` |
| 05 | 5 — Supply and source policy | `05_SUPPLY_AND_SOURCE_POLICY.md` |
| 06 | 6 — Untrusted import and company context | `06_UNTRUSTED_IMPORT_AND_COMPANY_CONTEXT.md` |
| 07 | 7 — Qualification and evidence policy | `07_QUALIFICATION_AND_EVIDENCE_POLICY.md` |
| 08 | 8 — Privacy and authorization | `08_PRIVACY_AND_AUTHORIZATION.md` |
| 09 | 9 — API, async, and failure contracts | `09_API_ASYNC_AND_FAILURE_CONTRACTS.md` |
| 10 | 10 — Responsive/accessibility component architecture | `10_RESPONSIVE_ACCESSIBILITY_ARCHITECTURE.md` |
| 11 | 11 — Opportunity Slate integration | `11_SLATE_INTEGRATION.md` |
| 12 | 12 — Observability and cost | `12_OBSERVABILITY_AND_COST.md` |
| 13 | 13 — Migration, release, and rollback | `13_MIGRATION_RELEASE_AND_ROLLBACK.md` |
| 14 | 14 — Final child graph | `14_FINAL_CHILD_GRAPH.md` |
| 15 | 15 — Decision register | `15_DECISION_REGISTER.md` |
| 16 | 16 — End-to-end traceability | `16_TRACEABILITY_MATRIX.md` |
| 17 | Completion record | `17_ARCHITECTURE_COMPLETION_REPORT.md` |
| 18 | Architecture acceptance record | `18_ARCHITECTURE_ACCEPTANCE.md` |

## Current verdict

**P0 architecture is complete, independently reviewed, merged, and accepted.**

- The sixteen required outputs passed independent review with zero findings
  (reviewed candidate `e040677f69b0fabf4ca97998dfcc867f1b55eec3`, reviewer
  session `0ce281ff-59fe-4ea3-b661-82d1111d74e1`).
- The architecture merged to `main` as
  `09262ea819f4a9a643a142a7a28a704de3fc839f` (Azure PR 605, normal squash, no
  policy bypass, `[skip ci]` documentation closeout). Nothing was deployed and
  production authority remains withheld.
- The `PS-MY-OPPORTUNITIES-001` claim is **closed** with that `merged_sha`;
  the reviewed implementation branch is preserved for squash-byte proof.
- Architecture acceptance is recorded in `18_ARCHITECTURE_ACCEPTANCE.md`:
  REC-01 through REC-08 are resolved in `15_DECISION_REGISTER.md` §2 and the
  doc 14 child graph is accepted exactly as written (doc 14 unchanged).

Acceptance is a decision record, not permission to build. No implementation
child is authorized, and every named deferral in `15_DECISION_REGISTER.md`
§3 remains open with its gate — provider identity and spending,
evidence-strength policy, freshness and closure thresholds, company context,
URL-fetch enablement, migration/cutover/rollback, production activation, and
the corrected desktop/iPad artwork behind the binding two-row search
invariant.

## Exact next step

The `PS-MY-OPPORTUNITIES-ARCHITECTURE-ACCEPTANCE-001` candidate returns
through the Codex program manager to an independent reviewer for exact-SHA
review. Only after that pass does its writer add the review receipt and the
fixed runtime-inert evidence file, run the merge preflight, and merge.

After that package merges and closes, the next program step is a
**separately activated** `C1` (`PS-MYOPP-SUPPLY-RIGHTS-001`) — documentation
only, pre-REC-02-safe, with no provider contact, selection, or spending. No
child is activated by this acceptance.
