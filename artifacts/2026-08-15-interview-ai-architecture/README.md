# PS-INTERVIEW-AI-ARCHITECTURE-001 — Interview Studio AI architecture

**Status:** Gate A delivered and awaiting Pete and Codex review. Gate B not started.
**Owner:** Pete.
**Lane class:** `direction_authority`, `production_capable: false`.
**Delivery path:** Protected — consequential AI, private retrieval, authorization, and
future data boundaries.
**Runtime status:** This package changes no application, route, template, stylesheet,
JavaScript, test, prompt, model, provider, schema, migration, configuration, pipeline,
or live behavior. It is documentation and evidence only.

## Why this package lives under `artifacts/` — open control-plane defect

This package's conventional home is `docs/initiatives/PS-INTERVIEW-AI-ARCHITECTURE-001/`.
It is delivered under `artifacts/2026-08-15-interview-ai-architecture/` instead because
those two locations are currently in conflict, and the lane cannot lawfully resolve it.

- `tests/test_package_registry.py::test_registry_accounts_for_every_initiative_once`
  requires every directory under `docs/initiatives/` to be listed exactly once in
  `docs/governance/PACKAGE_REGISTRY.json`.
- A `direction_authority` lane's writable surfaces are restricted by construction to
  `docs/initiatives` and `artifacts`
  (`DIRECTION_AUTHORITY_ALLOWED_ROOTS`, `scripts/delivery_preflight.py:620-623`;
  enforced at `:2587-2614`). `docs/governance/` is forbidden to this lane class.

Therefore a `direction_authority` lane can create a new package directory but can never
register it, and its pull request fails the required build. This was proven here: build
1106 for PR 501 failed on exactly this one assertion out of 3,779 tests.

There is no prior case. `PS-TRUST-SAFETY-001` is the only other `direction_authority`
package created since the registry test merged on 2026-08-14, and it was paused with its
package pushed but never merged, so it never reached this gate.

Both surfaces are declared writable for this lane, so delivering here is in scope and
requires no registry change. `PACKAGE_REGISTRY.json` describes itself as "a complete
rationalization index, not delivery authority," so nothing authoritative is lost by the
package being indexed later.

**Repair belongs to `PS-DELIVERY-CONTROL-001`, not to this lane.** Either the registry
test should tolerate a package directory belonging to a currently active lane, or
`docs/governance/PACKAGE_REGISTRY.json` should be addable by an activated lane creating
its own package. Once repaired, these files move to the `docs/initiatives/` path
unchanged. This lane did not work around the rule, weaken a control, or write outside its
recorded scope.

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
[`../PS-AI-AGENT-QUALITY-ROUND-2-001/OWNER_DECISION_CLOSEOUT_2026-08-15.md`](../../docs/initiatives/PS-AI-AGENT-QUALITY-ROUND-2-001/OWNER_DECISION_CLOSEOUT_2026-08-15.md),
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

**Gate A — current-system diagnosis. Delivered.**
[`01_GATE_A_CURRENT_SYSTEM_DIAGNOSIS.md`](01_GATE_A_CURRENT_SYSTEM_DIAGNOSIS.md)
returns a cited current-state map that separates confirmed behavior, source-supported
inference, live observation, and unverified behavior; a confirmed gap register; an
explicit list of what was not verified; and the owner decisions the diagnosis surfaces.
**Gate A stops here for Pete and Codex review.**

**Gate B — staged architecture. Not started.** Begins only on diagnosis acceptance, in
these reviewable increments, each carrying purpose, input manifest, output schema,
deterministic guardians, failure behavior, evaluation slice, and version identity:

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

- [`docs/initiatives/PS-AI-AGENT-QUALITY-ROUND-2-001/README.md`](../../docs/initiatives/PS-AI-AGENT-QUALITY-ROUND-2-001/README.md)
- [`docs/initiatives/PS-AI-AGENT-QUALITY-ROUND-2-001/01_AI_SURFACE_SEQUENCE.md`](../../docs/initiatives/PS-AI-AGENT-QUALITY-ROUND-2-001/01_AI_SURFACE_SEQUENCE.md)
- [`docs/initiatives/PS-AI-AGENT-QUALITY-ROUND-2-001/02_INTERVIEW_STUDIO_AI_DOSSIER.md`](../../docs/initiatives/PS-AI-AGENT-QUALITY-ROUND-2-001/02_INTERVIEW_STUDIO_AI_DOSSIER.md)
- [`docs/initiatives/PS-AI-AGENT-QUALITY-ROUND-2-001/03_INTERVIEW_STUDIO_GOLDEN_CASES.md`](../../docs/initiatives/PS-AI-AGENT-QUALITY-ROUND-2-001/03_INTERVIEW_STUDIO_GOLDEN_CASES.md)
- [`docs/initiatives/PS-AI-AGENT-QUALITY-ROUND-2-001/04_INTERVIEW_STUDIO_SCORECARD.md`](../../docs/initiatives/PS-AI-AGENT-QUALITY-ROUND-2-001/04_INTERVIEW_STUDIO_SCORECARD.md)
- [`docs/initiatives/PS-AI-AGENT-QUALITY-ROUND-2-001/05_CHATGPT_WORK_OWNER_REVIEW.md`](../../docs/initiatives/PS-AI-AGENT-QUALITY-ROUND-2-001/05_CHATGPT_WORK_OWNER_REVIEW.md)
- [`docs/initiatives/PS-AI-AGENT-QUALITY-ROUND-2-001/06_INTERVIEW_AI_OWNER_DECISIONS.md`](../../docs/initiatives/PS-AI-AGENT-QUALITY-ROUND-2-001/06_INTERVIEW_AI_OWNER_DECISIONS.md)
- [`docs/initiatives/PS-AI-AGENT-QUALITY-ROUND-2-001/07_INTERVIEW_AI_ACCEPTED_DIRECTION_CONTINUATION.md`](../../docs/initiatives/PS-AI-AGENT-QUALITY-ROUND-2-001/07_INTERVIEW_AI_ACCEPTED_DIRECTION_CONTINUATION.md)
- [`docs/initiatives/PS-AI-AGENT-QUALITY-ROUND-2-001/OWNER_DECISION_CLOSEOUT_2026-08-15.md`](../../docs/initiatives/PS-AI-AGENT-QUALITY-ROUND-2-001/OWNER_DECISION_CLOSEOUT_2026-08-15.md)

Preserved adjacent authority — **integrate with, do not independently redesign**:

- [`docs/initiatives/PS-INTERVIEW-ROLE-CONTEXT-001/README.md`](../../docs/initiatives/PS-INTERVIEW-ROLE-CONTEXT-001/README.md)
- [`docs/initiatives/PS-INTERVIEW-ROLE-CONTEXT-001/COMPLETION_REPORT.md`](../../docs/initiatives/PS-INTERVIEW-ROLE-CONTEXT-001/COMPLETION_REPORT.md)
- [`docs/initiatives/PS-INTERVIEW-ROLE-CONTEXT-001/O_NET_RECOVERY_STATUS.md`](../../docs/initiatives/PS-INTERVIEW-ROLE-CONTEXT-001/O_NET_RECOVERY_STATUS.md)

Site and governance authority:

- [`docs/PEERSLATE_SITE_RULES.md`](../../docs/PEERSLATE_SITE_RULES.md)
- the current Constitution and Roadmap named by
  [`docs/governance/CURRENT_BASELINE.yaml`](../../docs/governance/CURRENT_BASELINE.yaml)

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
- No paid provider call, evaluation execution, production member data use, or
  launch-threshold selection. "Wave 1" means design the evaluation execution plan only.
- No provider switch, Azure AI Search deployment, or premature retrieval implementation.
- No Opportunity Slate AI, Ask Pete, Workshop AI, O*NET, Community, Profile, or Journal
  architecture or implementation in this package.
- No material Interview Studio visual redesign; a material visual decision returns to
  ChatGPT and Pete as a concise brief under the visual-integrity standard.
- No grant, merge, deployment, enablement, or live claim before Pete and Codex review.

## Review return

Gate A returns to Pete and Codex. Pete accepts, revises, or rejects the diagnosis before
Gate B begins. Any runtime implementation requires its own separate Protected activation.
