# PS-AI-OPS-LEAN-001 - Lean Delivery and Audit Policy

## Assignment

- Owner decision: Pete, 2026-07-24
- Designated manager: current ChatGPT Work/Codex task
- Sole writer: Codex governance writer
- Branch: `work/2026-07-24-lean-ai-delivery-audits`
- Base: `origin/main` at `15e38cb1f55e9a5a736d1c493b1af7cd88d15f91`
- Focused recheck: Pass - fresh Sol High review of
  `40464edbea5c9ff75a6f6969419fc5099542fa6e`
- Status: Pass for technical readiness; Azure PR 170 is open and not merged

## Purpose

Make one lean, symmetrical Codex/Claude delivery process authoritative without
removing the quality controls that protect PeerSlate members, product truth, or
release safety.

## Scope

1. Centralize stable roles and current model versions in
   `docs/AI_MODEL_AND_ROLE_ROUTING.md`.
2. Require one architecture pass only when architecture is needed; one writer
   self-review; one risk-triggered independent review; same-writer corrections;
   Pete's final visual review of the corrected build; and normal release proof.
3. Add checkpoint, readiness, full-site, and triggered audit policy without
   replaying every implementation review.
4. Make `AGENTS.md` and `CLAUDE.md` inherit the same process, without hardcoded
   Bible/Roadmap versions in `CLAUDE.md`.
5. Record the owner decision, this package, its completion report, and focused
   guardrail coverage.
6. Apply the accepted independent-review corrections: a lightweight audit
   register, portable pointer-closeout guidance, and the active protected Slice
   1 delivery route.

## Explicit quality controls retained

- complete-diff self-review and pre-merge verification;
- applicable focused, guardrail, accessibility, privacy, migration, and runtime
  checks;
- mandatory independent review for the defined high-risk triggers;
- Pete's final visual acceptance for material user-facing work;
- Azure PR/squash, runtime pipeline, live verification, truthful status, and
  rollback/stop evidence; and
- compact `Pass`, `Conditional`, or `Fail` evidence for every slice and audit.

## Writable files

- `AGENTS.md`
- `CLAUDE.md`
- `docs/AI_WORKFLOW.md`
- `docs/AI_MODEL_AND_ROLE_ROUTING.md`
- `docs/governance/DECISIONS.md`
- `docs/governance/AI_DELIVERY_AUDIT_REGISTER.md`
- `docs/governance/MANAGER_SESSION_HANDOFF.md`
- `docs/initiatives/PS-SLATE-STUDIO-IA-001/README.md`
- `docs/initiatives/PS-SLATE-STUDIO-IA-001/08_D6_SLICE_1_ACTIVATION_PROPOSAL.md`
- `docs/initiatives/PS-SLATE-STUDIO-IA-001/11_OWNER_ACTIVATION_AND_CODEX_MANAGER_GATE.md`
- this initiative directory
- directly relevant governance/site-rule tests

## Exclusions

No change to current baseline/state/initiative records, Bible, Roadmap, runtime
code, feature flags, deployment configuration, Azure pipeline, route, schema,
or production behavior is authorized. A governance merge is not a production
feature release.

## Acceptance criteria

1. The central workflow states the lean delivery route, mandatory risk triggers,
   retained release controls, and audit cadence.
2. Central routing names the approved Codex and Claude architect, implementer,
   and reviewer choices, with periodic model verification.
3. Claude no longer contains a hardcoded Bible/Roadmap version and clearly
   inherits the same lean process.
4. The owner decision is recorded without changing product or runtime truth.
5. Focused governance and site-rule tests plus `git diff --check` pass.
6. The audit register has an owner, completed-slice definition, current count,
   cadence dates, reset/phase-boundary rule, and non-recursive correction rule.
7. The active protected Slice 1 package preserves its required independent
   review while using the central lean route.
