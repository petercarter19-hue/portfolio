# PS-INTERVIEW-AI-ARCHITECTURE-001 — Interview Studio AI architecture

**Status:** v2.8 architecture accepted by Pete on 2026-08-16, including D3, D8, and D9
as recommended. The package is now relocated and registered under D13 and awaits fresh
exact-SHA review plus Pete's approval of that exact relocated SHA before any merge
grant. Gate A and Gate B are delivered; nine correction rounds are applied —
six Codex reconciliation rounds and three manager passes with mandatory internal review
— with every round's change register in
[`21_CODEX_RECONCILIATION.md`](21_CODEX_RECONCILIATION.md).
**Start here:** [`00_CONSOLIDATED_ARCHITECTURE.md`](00_CONSOLIDATED_ARCHITECTURE.md) — the
only normative document. The five detail sections are non-normative historical drafts.
**Owner:** Pete.
**Package manager:** ChatGPT Work, the Pete-designated management role.
**Initial architect/sole writer through `3fcdb917`:** the assigned Claude Interview AI
session.
**Current sole repository writer/technical reconciler:** Codex, after the control-only
writer transfer merged as `6c188980`.
**Independent review:** fresh, read-only Codex reviewers.
**Material visual creator for later visual slices:** Original ChatGPT; Pete remains the
final visual and product decision-maker.
**Lane class:** `direction_authority`, `production_capable: false`.
**Delivery path:** Protected — consequential AI, private retrieval, authorization, and
future data boundaries.
**Runtime status:** This package changes no application, route, template, stylesheet,
JavaScript, test, prompt, model, provider, schema, migration, configuration, pipeline,
or live behavior. It is documentation and evidence only.

## Permanent package location — D13 repair completed

This package now lives at its permanent home:
`docs/initiatives/PS-INTERVIEW-AI-ARCHITECTURE-001/`.

- `tests/test_package_registry.py::test_registry_accounts_for_every_initiative_once`
  requires every directory under `docs/initiatives/` to be listed exactly once in
  `docs/governance/PACKAGE_REGISTRY.json`.
- A `direction_authority` lane's writable surfaces are restricted by construction to
  `docs/initiatives` and `artifacts`
  (`DIRECTION_AUTHORITY_ALLOWED_ROOTS`, `scripts/delivery_preflight.py:620-623`;
  enforced at `:2587-2614`). `docs/governance/` is forbidden to this lane class.

That conflict was proven here: build 1106 for PR 501 failed on exactly this one assertion
out of 3,779 tests. The package was temporarily relocated to `artifacts/`, the rebuild
passed, and PR 501 merged as `6b3f90d5` — the failure and the merge are the same PR before
and after that temporary relocation.

There is no prior case. `PS-TRUST-SAFETY-001` is the only other `direction_authority`
package created since the registry test merged on 2026-08-14, and it was paused with its
package pushed but never merged, so it never reached this gate.

**D13 resolved the conflict through `PS-DELIVERY-CONTROL-001`.** Control PR 506 merged as
`b4d79b217b1b8b68128a5271031390bb2be521b6` after build 1142 and all three policies
passed. It reconciled the durable owner-authority record and admitted exactly this move
plus one `future_finish` registry entry. This candidate performs the move, normalizes the
relative links, and increments only `counts.future_finish` and `counts.total`. The repair
does not weaken the registry test, create a general lane-class exception, or grant merge,
release, provider-call, deployment, enablement, or live authority. Fresh exact-SHA review
and Pete's approval of that exact relocated SHA remain required before the later grant.

## Purpose

Translate Pete's accepted Interview Studio AI direction into an owner-reviewable
architecture: versioned specialist instructions, deterministic guardians, knowledge
manifests, schemas, evaluation design, telemetry, rollback, and bounded future
implementation packages.

This is **Interview Studio AI only**. It is not a site-wide AI redesign, and it does not
collapse the specialists into one generic assistant.

## Owner decisions governing this package

**2026-08-15 — sequence.** Pete directed: *"Proceed with Interview AI first."* This is
Pete's latest owner decision and deliberately changes the earlier sequence recorded in
[`../PS-AI-AGENT-QUALITY-ROUND-2-001/OWNER_DECISION_CLOSEOUT_2026-08-15.md`](../PS-AI-AGENT-QUALITY-ROUND-2-001/OWNER_DECISION_CLOSEOUT_2026-08-15.md),
which named the Opportunity Slate read-first diagnostic as the next activation.
Opportunity Slate remains a required protected diagnostic and is **queued, not
canceled**; it does not precede this assignment.

**2026-08-15 — accepted handoff corrections.** Use a `direction_authority` lane with
`production_capable: false` while keeping the Protected delivery path; use this child
package rather than resuming the paused parent; split delivery into Gate A and Gate B;
preserve and integrate with the existing Role Context contract; resolve the reading list
to complete repository paths; and treat "Wave 1 execution" as evaluation-plan design
only.

## Gates

**Gate B — staged architecture. Delivered.** Five sections written in parallel
(`10`–`14_SECTION_*.md`), then independently reviewed (`20_INDEPENDENT_REVIEW.md`, 31
findings, verdict REVISE), then reconciled in
[`00_CONSOLIDATED_ARCHITECTURE.md`](00_CONSOLIDATED_ARCHITECTURE.md), which rules on all ten
blocking findings. The sections are deliberately left unedited so the disagreements remain
auditable. **Authenticated evidence** from a bounded five-call synthetic test against
production is in [`03_AUTHENTICATED_EVIDENCE.md`](03_AUTHENTICATED_EVIDENCE.md).

**Gate A — current-system diagnosis. Delivered.**
[`01_GATE_A_CURRENT_SYSTEM_DIAGNOSIS.md`](01_GATE_A_CURRENT_SYSTEM_DIAGNOSIS.md)
returns a cited current-state map that separates confirmed behavior, source-supported
inference, live observation, and unverified behavior; a confirmed gap register; an
explicit list of what was not verified; and the owner decisions the diagnosis surfaces.
Gate A originally stopped here for review. Its files **did merge to `main`** (PR 501,
merge commit `6b3f90d5`) before that review — a process fault recorded honestly as
errata E7 — and Pete ratified the documentation-only merge for continuity on
2026-08-16; the manager's 2026-08-15 update authorized continuing into Gate B. The
no-merge-before-review exclusion below is the lane's forward-looking rule and was not
repeated: Gate B sits on the open, unmerged PR 502.

**Gate B increments as originally planned** — all now delivered; this list records the
assignment's shape, not current status:

1. Shared Constitution, versioning, and Diagnostician/Router
2. Answer Coach and Revision Partner
3. Private History Nudge and private retrieval
4. Grounded Example and Generic Example
5. Consolidated orchestration, evaluation, failure, rollback, and implementation sequence

The Role-Context-bound Question Generator is future architecture only and is not made
active in the first implementation sequence.

## Required authority — complete repository paths

Parent direction package (paused, read-only authority here — **do not resume or
rewrite**):

- [`docs/initiatives/PS-AI-AGENT-QUALITY-ROUND-2-001/README.md`](../PS-AI-AGENT-QUALITY-ROUND-2-001/README.md)
- [`docs/initiatives/PS-AI-AGENT-QUALITY-ROUND-2-001/01_AI_SURFACE_SEQUENCE.md`](../PS-AI-AGENT-QUALITY-ROUND-2-001/01_AI_SURFACE_SEQUENCE.md)
- [`docs/initiatives/PS-AI-AGENT-QUALITY-ROUND-2-001/02_INTERVIEW_STUDIO_AI_DOSSIER.md`](../PS-AI-AGENT-QUALITY-ROUND-2-001/02_INTERVIEW_STUDIO_AI_DOSSIER.md)
- [`docs/initiatives/PS-AI-AGENT-QUALITY-ROUND-2-001/03_INTERVIEW_STUDIO_GOLDEN_CASES.md`](../PS-AI-AGENT-QUALITY-ROUND-2-001/03_INTERVIEW_STUDIO_GOLDEN_CASES.md)
- [`docs/initiatives/PS-AI-AGENT-QUALITY-ROUND-2-001/04_INTERVIEW_STUDIO_SCORECARD.md`](../PS-AI-AGENT-QUALITY-ROUND-2-001/04_INTERVIEW_STUDIO_SCORECARD.md)
- [`docs/initiatives/PS-AI-AGENT-QUALITY-ROUND-2-001/05_CHATGPT_WORK_OWNER_REVIEW.md`](../PS-AI-AGENT-QUALITY-ROUND-2-001/05_CHATGPT_WORK_OWNER_REVIEW.md)
- [`docs/initiatives/PS-AI-AGENT-QUALITY-ROUND-2-001/06_INTERVIEW_AI_OWNER_DECISIONS.md`](../PS-AI-AGENT-QUALITY-ROUND-2-001/06_INTERVIEW_AI_OWNER_DECISIONS.md)
- [`docs/initiatives/PS-AI-AGENT-QUALITY-ROUND-2-001/07_INTERVIEW_AI_ACCEPTED_DIRECTION_CONTINUATION.md`](../PS-AI-AGENT-QUALITY-ROUND-2-001/07_INTERVIEW_AI_ACCEPTED_DIRECTION_CONTINUATION.md)
- [`docs/initiatives/PS-AI-AGENT-QUALITY-ROUND-2-001/OWNER_DECISION_CLOSEOUT_2026-08-15.md`](../PS-AI-AGENT-QUALITY-ROUND-2-001/OWNER_DECISION_CLOSEOUT_2026-08-15.md)

Preserved adjacent authority — **integrate with, do not independently redesign**:

- [`docs/initiatives/PS-INTERVIEW-ROLE-CONTEXT-001/README.md`](../PS-INTERVIEW-ROLE-CONTEXT-001/README.md)
- [`docs/initiatives/PS-INTERVIEW-ROLE-CONTEXT-001/COMPLETION_REPORT.md`](../PS-INTERVIEW-ROLE-CONTEXT-001/COMPLETION_REPORT.md)
- [`docs/initiatives/PS-INTERVIEW-ROLE-CONTEXT-001/O_NET_RECOVERY_STATUS.md`](../PS-INTERVIEW-ROLE-CONTEXT-001/O_NET_RECOVERY_STATUS.md)

Site and governance authority:

- [`docs/PEERSLATE_SITE_RULES.md`](../../PEERSLATE_SITE_RULES.md)
- the current Constitution and Roadmap named by
  [`docs/governance/CURRENT_BASELINE.yaml`](../../governance/CURRENT_BASELINE.yaml)

## Frozen product direction

The architecture must preserve the accepted direction in full. In particular: Interview
AI proposes and the member decides; the product is session-free with no Interview Session
object; original answers and versions are preserved; identity is server-derived and
authorization precedes every protected retrieval; private History is member-owned and
revocable; a nudge searches only that member's History and returns bounded metadata and
an excerpt before selection; external and member-supplied text is untrusted content and
never instructions; no Journal dependency; O*NET stays future attributed knowledge;
nothing is invented; no ranking, hiring prediction, or protected-trait inference;
responses are semantically structured; answer length follows the question's actual
obligations with no universal rule; failure states are distinct and truthful; routine
telemetry is content-free; and no AI result silently saves, publishes, sends, deletes, or
changes canonical truth.

## Exclusions

- No application, route, template, stylesheet, JavaScript, test, prompt, model, provider,
  schema, migration, index, API, configuration, dependency, pipeline, deployment,
  production-data, or live-behavior change.
- No evaluation execution, production member data use, or launch-threshold selection.
  "Wave 1" means design the evaluation execution plan only. One owner-authorized exception
  occurred: Pete approved a bounded authenticated test on 2026-08-15 in which exactly five
  application AI requests were made with synthetic content
  ([`03_AUTHENTICATED_EVIDENCE.md`](03_AUTHENTICATED_EVIDENCE.md)); the durable lane record
  now records that authorization through the completed D13 admission. No further provider
  request or evaluation execution is authorized by this package.
- No provider switch, Azure AI Search deployment, or premature retrieval implementation.
- No Opportunity Slate AI, Ask Pete, Workshop AI, O*NET, Community, Profile, or Journal
  architecture or implementation in this package.
- No material Interview Studio visual redesign; a material visual decision returns to
  ChatGPT and Pete as a concise brief under the visual-integrity standard.
- No merge, release, deployment, enablement, or live claim. A later grant remains blocked
  until fresh exact-SHA review and Pete's approval of that exact relocated SHA.

## Review return

Pete accepted v2.8 and D3, D8, and D9 as recommended on 2026-08-16. This relocated
candidate now returns for one fresh exact-SHA review. Pete then approves or rejects that
exact SHA; PR 502 remains unmerged until he approves it and the separate grant enters
`main`. Any runtime implementation still requires its own Protected activation per slice.
