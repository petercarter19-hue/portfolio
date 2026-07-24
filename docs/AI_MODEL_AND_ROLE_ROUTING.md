# PeerSlate AI Model and Role Routing

**Operational standard:** July 24, 2026

This is the central authority for model versions and stable delivery roles.
Packages name roles, not model versions. Verify the available model and resolved
alias before each major package, at each quarterly audit, and whenever
the active surface changes; availability, limits, and aliases can change without
changing this delivery policy.

## Lean operating model

PeerSlate uses one pass for each distinct responsibility:

```text
architect only when architecture is needed
        ↓
one sole writer implements, tests, and self-reviews the complete diff
        ↓
one fresh independent reviewer only for a defined risk trigger
        ↓
the same writer corrects accepted findings and refreshes evidence
        ↓
Pete gives final visual acceptance on the corrected build when material visual work applies
        ↓
Azure PR, pipeline, live verification, and compact closeout
```

Do not ask another model to recreate accepted architecture, repeat a complete
technical audit, or run a documentation-only deployment. When architecture is
accepted, do not send it to another premium model to recreate it. A model switch
alone does not establish independent review.

## Stable role rules

- Each package names exactly one manager and one active writer. The manager
  owns product decisions, scope, sequencing, shared-governance reservations,
  visual authority, conflict resolution, and final scope/product readiness.
- The architect is used only for new or materially changed architecture. Preserve
  its accepted package; a second architect is an escalation, not normal process.
- The writer owns implementation, complete-diff self-review, corrections, tests,
  evidence, PR readiness, and approved release/closeout.
- A fresh independent reviewer is review-only. It challenges the exact package,
  diff, SHA, and evidence; it does not receive an open-ended redesign brief.
- The original writer fixes accepted findings. Recheck only an unresolved or
  conditional finding unless the correction changes risk or architecture.
- Pete is the final visual reviewer for material user-facing work and reviews the
  corrected real build. The manager does not repeat the technical audit.
- Handoffs use repository artifacts, branch, exact full SHA, evidence, known
  gaps, and forbidden scope—not a chat transcript.
- A governance-only package may assign its manager as sole writer when no second
  writer is active; it still receives complete-diff review and applicable tests.

## Mandatory independent-review triggers

A fresh independent reviewer is required for the exact branch/SHA evidence when:

1. architecture-heavy changes;
2. authentication, session, authorization, privacy, or cross-user data;
3. schema or migration work;
4. publication, audience, or deletion behavior;
5. consequential AI behavior;
6. shared infrastructure;
7. conflicting evidence; or
8. an explicit package risk control.

Ordinary bounded work skips architecture unless it needs it and skips the
independent reviewer unless one of these triggers applies. The required
pre-merge tests, complete-diff self-review, evidence, release truth, and
rollback/stop controls remain in every applicable package.

## Current OpenAI / Codex routing

| Stable role | Current choice | Use |
|---|---|---|
| Architect | **GPT-5.6 Sol, Extra High** | New or materially changed product, data, privacy, or technical architecture |
| Implementer | **GPT-5.6 Terra, Extra High** | Bounded repository implementation, tests, documentation, corrections, and closeout |
| Independent reviewer | **Fresh GPT-5.6 Sol, High** | Exact-SHA, risk-triggered review and audit findings |

Use a smaller capable tool for read-only inventory, extraction, formatting, or
test-log reduction. Do not lower a required role's evidence standard because a
model, plan, or cost limit changes; record an exception and obtain direction
when the specified role is unavailable.

## Current Claude routing

| Stable role | Current choice | Use |
|---|---|---|
| Architect | **Claude Fable 5** | New or materially changed product, data, privacy, or technical architecture |
| Implementer | **Claude Sonnet 5** | Bounded Claude Code implementation, tests, documentation, corrections, and closeout |
| Independent reviewer | **Claude Opus 4.8** | Exact-SHA, risk-triggered review and audit findings |

In Claude Code, confirm the resolved model with `/model` and `/status` before a
major package or audit. Do not treat a remembered marketing nickname or an
`opusplan` alias as evidence that the required role is active.

## Delivery routes

### Architecture or high-risk package

1. One architect creates or updates the durable package only where architecture
   is needed.
2. The manager confirms the bounded scope and visual/truth authority.
3. One implementer builds, tests, self-reviews, and returns exact evidence.
4. One fresh independent reviewer addresses the defined risk question.
5. The same implementer corrects accepted findings and reruns affected evidence.
6. Pete reviews the corrected build for material visual work; the manager gives
   scope/product-readiness acceptance; then release proceeds.

### Ordinary bounded package

1. The manager supplies an accepted package and the writer confirms scope.
2. One implementer builds, tests, self-reviews, corrects findings, and returns
   evidence.
3. Add one reviewer only when a mandatory trigger applies.
4. Obtain applicable acceptance, then release and close out.

### Mechanical or governance propagation

1. One capable writer performs the bounded update and complete-diff review.
2. Run deterministic checks and the relevant guardrails.
3. Use a premium reviewer only when product meaning changes, evidence conflicts,
   or another mandatory trigger applies.
4. Do not deploy merely to record documentation.

## Audit role and reporting

The audit cadence and trigger conditions live in `docs/AI_WORKFLOW.md`. An audit
uses one fresh reviewer in the active ecosystem, exact evidence and SHAs, and a
compact ranked `Pass`, `Conditional`, or `Fail` report with owners and one next
action. It samples cross-system drift rather than replaying every implementation
review. Escalate to a deeper architect review only when an audit finding raises a
real architecture question.

## Visual workflow

```text
ChatGPT creates the complete production-intent visual and state set
→ Pete selects and locks one exact durable authority
→ manager records interaction, truth, and accessibility contract
→ one writer implements and compares the real build at required states/viewports
→ one reviewer only if a defined risk trigger applies
→ same writer corrects findings
→ Pete reviews the corrected real build for final visual acceptance
→ Azure release evidence and live verification
```

ChatGPT is the sole visual-creation surface for new or materially revised
PeerSlate authority. This rule covers concepts, mockups, storyboards, responsive
and state sets, style exploration, and image generation or editing. Authorities
Pete locked before 2026-07-24 remain valid until materially revised. Codex and
Claude implementers may translate the exact locked authority into code, capture
implementation screenshots, report parity, usability, truth, or accessibility
findings, and make documented non-material adaptations for semantic structure,
focus, WCAG contrast, touch targets, reduced motion, truthful state wiring, or
text reflow. Those evidence and implementation activities are not new visual
design. Claude Chat, Co-Work, Code, and Design may not originate or substitute
the visual authority. A change to composition, hierarchy, dominant
object/action, typography family, color language, or responsive interaction
model is material and returns to ChatGPT and Pete for a revised exact lock.

A visual acceptance does not replace accessibility, truth, security/privacy, or
release checks.

## Handoff requirements

Every substantial handoff contains:

1. package, status, owner decision, manager, and sole writer;
2. authoritative base, branch, exact full SHA, and ownership status;
3. governing requirements, visual authority, truth boundary, exclusions, and
   whether a review trigger applied;
4. changed files and migration/infrastructure impact;
5. tests and exact results, evidence, and accepted deviations;
6. findings, risks, conflicts, stop controls, and next action; and
7. PR, pipeline, deployment, and live status stated separately.

## PS-AI-OPS requirements

- **PS-AI-OPS-001:** One package has one designated manager and one active
  branch writer.
- **PS-AI-OPS-002:** Architecture is authored once, only when needed, and stored
  durably.
- **PS-AI-OPS-003:** The writer self-reviews the complete diff before handoff.
- **PS-AI-OPS-004:** Independent review is risk-based, fresh, exact-SHA, and
  review-only.
- **PS-AI-OPS-005:** The same writer fixes accepted review findings and reruns
  affected evidence.
- **PS-AI-OPS-006:** Pete gives final visual acceptance for material visual work
  after corrections.
- **PS-AI-OPS-007:** Pre-merge verification, runtime pipeline, live verification,
  rollback/stop controls, and truthful status boundaries remain required.
- **PS-AI-OPS-008:** Checkpoint, readiness, full-site, and triggered audits use
  the workflow cadence and one fresh reviewer.
- **PS-AI-OPS-009:** Packages use stable role names; this document is the
  periodically verified model-version authority.
- **PS-AI-OPS-010:** Cross-vendor work is used only for a bounded independent
  risk question, never to duplicate the delivery route.
- **PS-AI-OPS-011:** ChatGPT is the sole creator of new or materially revised
  production-intent visual authority. Existing Pete-locked authorities remain
  valid; implementation/review agents may compare and make documented
  non-material accessibility, truth, and reflow adaptations, but may not create
  a competing or substitute design.
