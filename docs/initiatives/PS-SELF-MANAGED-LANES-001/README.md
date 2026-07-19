# PS-SELF-MANAGED-LANES-001 - Self-Managed Delivery Operating Model

## Assignment

- Owner decision: Pete, 2026-07-19
- Writer: ChatGPT Work governance lane
- Branch: `work/2026-07-19-self-managed-lanes`
- Base: `origin/main` at `eede8565d703a466bd788962d494e8b385b53409`
- Scope: workflow, authority/state, agent entry instructions, completion report,
  guardrail tests, manager handoff, and the current Voice visual-correction
  allocation only

## Outcome

Make Codex and Claude self-managed delivery lanes. Each assigned writer owns
implementation, complete-diff review, correction, tests, evidence, PR readiness,
and post-acceptance release/closeout. ChatGPT Work remains the task manager,
shared-authority/file-boundary coordinator, visual authority, exception
escalation point, and final product-acceptance room.

## Acceptance criteria

1. `docs/AI_WORKFLOW.md` is the canonical self-managed contract.
2. `AGENTS.md` and `CLAUDE.md` point every agent to that contract.
3. Writers return `Pass`, `Conditional`, or `Fail` self-certification with exact
   evidence and do not hide failures or conflicts.
4. A writer retains branch ownership through approved release/closeout unless a
   different writer takes over, in which case exact branch/SHA handoff remains
   mandatory.
5. Pete/ChatGPT Work retain final acceptance for material user-facing work but
   may rely on coherent self-certified reports instead of repeating the full
   audit.
6. Azure PR/squash/pipeline, credential safety, server-enforced authorization,
   one-writer-per-branch, and honest release-status rules remain unchanged.
7. Package-local architecture/evidence travels with the branch; shared authority
   records change only under explicit reservation; the Bible is not used as a
   routine changelog.
8. Current records reflect the released-but-visually-reopened Voice state and
   give Claude an exact truth-safe visual-correction allocation.
9. Governance and full test suites pass.

## Writable files

- `START_HERE.md`, `AGENTS.md`, `CLAUDE.md`
- `docs/AI_WORKFLOW.md`
- `docs/PEERSLATE_SITE_RULES.md`
- `docs/governance/*` current workflow/state/decision/handoff records
- `docs/templates/OWNER_TECHNICAL_COMPLETION_REPORT.md`
- `docs/initiatives/PS-VOICE-001/README.md` and visual correction addendum
- this initiative directory
- governance/site-rule guardrail tests

No application behavior, route, template, CSS, JavaScript, SQL, migration,
infrastructure, identity, or production configuration change is authorized.

## Closeout

Use `docs/templates/OWNER_TECHNICAL_COMPLETION_REPORT.md`, push the exact branch,
release through Azure PR/squash/pipeline, verify production routes are unchanged,
and record exact release evidence without claiming that the Voice visual
correction itself shipped in this governance package.
