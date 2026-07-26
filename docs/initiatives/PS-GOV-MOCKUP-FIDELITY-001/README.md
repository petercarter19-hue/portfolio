# PS-GOV-MOCKUP-FIDELITY-001 - Continuous approved-mockup fidelity

## Assignment and status

- Owner decision: Pete, 2026-07-26
- Designated manager and sole governance writer: current ChatGPT Work/Codex task
- Branch: `work/2026-07-26-mockup-authority-rule-001`
- Base: Azure `origin/main` at
  `9d01fa7315115599bae0b45c237b72b265ac24e8`
- Status: **Pass** at clarified policy source
  `df499613ca848138dbea263270a9774973dd95ea`; owner authorized official
  release on 2026-07-26; Azure PR 181 squash-merged to `main` at
  `4db44270b524c77556b601c82d036b7af9d1c802`; automatic pipeline 245
  (`20260726.4`) passed Build and Deploy

## Owner decision

Whenever a PeerSlate experience is based on a Pete-approved mockup, that exact
mockup remains the primary visual authority throughout implementation, review,
correction, acceptance, and release. It is never merely first-pass inspiration.

Pete clarified on 2026-07-26 that the mandatory autonomous agent inspection loop
applies when he is not personally performing the visual inspection. The package
must record the visual inspector.

When Pete is not personally inspecting, the assigned writer/agent must review
the authority, implement a bounded pass, render the real result, review the
authority again, compare the two, correct every mismatch, and repeat that
compare-refine loop without a fixed iteration limit until the implementation
reaches exact visual parity at the corresponding state and viewport. A later
change that can affect the visual result reopens the same loop.

When Pete personally performs the inspection, he compares the approved mockup
with the real renders, directs corrections, decides whether another pass is
required, and gives or withholds final visual acceptance. The writer implements
his directions, returns updated renders, and records Pete's final visual
decision. A duplicate autonomous agent inspection or mismatch register is not
required unless Pete asks for or delegates it.

Functional correctness, passing tests, a recognizable resemblance, a first-pass
handoff, time pressure, or a plan to polish later cannot close the visual gate.
Truthful content, accessibility, and responsive reflow remain mandatory; they
must be handled through the narrow documented adaptation or revised-authority
path rather than by silently drifting from the approved mockup.

## Purpose

Make the owner's anti-drift rule durable across every supported agent and
delivery surface by:

1. defining the continuous compare-refine loop in the controlling Owner Visual
   Integrity Standard;
2. making the exact approved mockup the continuing comparison baseline rather
   than a one-time starting reference;
3. requiring a compact iteration and mismatch-closure record in the completion
   evidence when Pete is not personally performing the visual inspection, and a
   Pete-directed correction and final-decision record when he is;
4. preventing implementation screenshots, framework defaults, reviewer taste,
   or the current build from becoming a substitute authority; and
5. adding deterministic repository tests so the rule cannot silently disappear
   from the controlling workflow.

## Writable files

- `START_HERE.md`
- `AGENTS.md`
- `CLAUDE.md`
- `docs/AI_WORKFLOW.md`
- `docs/AI_MODEL_AND_ROLE_ROUTING.md`
- `docs/PEERSLATE_SITE_RULES.md`
- `docs/governance/AGENT_STARTUP_CHECKLIST.md`
- `docs/governance/DECISIONS.md`
- `docs/governance/DOCUMENT_CONTROL.md`
- `docs/governance/OWNER_VISUAL_INTEGRITY_STANDARD.md`
- `docs/templates/OWNER_TECHNICAL_COMPLETION_REPORT.md`
- this initiative directory
- directly relevant governance guardrail tests

## Exclusions

- No runtime route, template, stylesheet, JavaScript, image, data, schema,
  migration, dependency, feature flag, deployment configuration, or production
  behavior changes.
- No change to a currently locked visual authority or active product package.
- No change to the controlling Bible or Roadmap files or their hashes.
- No change to `CURRENT_BASELINE.yaml`, `CURRENT_STATE.md`, or
  `ACTIVE_INITIATIVES.md`; this package changes the operational enforcement of
  an existing constitutional visual promise, not an authority pointer, package
  assignment, runtime status, or verified production boundary.
- No merge or deployment claim merely because this task branch is committed or
  pushed.

## Acceptance criteria

1. The Owner Visual Integrity Standard defines the required review, implement,
   render, compare, refine, and repeat loop with no fixed maximum iteration
   count for agent-run inspection when Pete is not personally performing the
   visual inspection.
2. The standard states that an approved mockup remains the primary visual
   authority throughout delivery and that implementation evidence cannot
   replace it.
3. The standard defines Pete-run inspection without a duplicate autonomous
   agent inspection: Pete directs corrections and gives or withholds final
   visual acceptance, while the writer implements and records that cycle.
4. For agent-run inspection, exact comparable-state and comparable-viewport
   parity is the completion condition; every unresolved mismatch is corrected
   or the work reports `Conditional` or `Fail` and returns through the governed
   authority path.
5. Agent startup, shared workflow, Claude routing, model/role routing, site
   rules, and completion reporting all point to the same rule without creating
   an alternate visual process.
6. Focused governance/site-rule tests and `git diff --check` pass.
7. The completion report records the exact base/final SHA, changed files,
   complete-diff self-review, tests, scope exclusions, and the honest
   documentation-only production boundary.

## Exit gate

Commit and push the exact task branch to Azure `origin`, then return the branch,
full SHA, validation results, and owner-review/release status. The rule becomes
shared repository authority only after an accepted Azure pull request merges to
`main`.
