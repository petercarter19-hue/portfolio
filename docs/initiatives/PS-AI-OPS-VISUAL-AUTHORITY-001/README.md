# PS-AI-OPS-VISUAL-AUTHORITY-001 - ChatGPT visual-authority creation

## Assignment and status

- Owner decision: Pete, 2026-07-24
- Designated manager and governance writer: current ChatGPT Work/Codex task
- Branch: `codex/2026-07-24-chatgpt-visual-authority`
- Base: Azure `origin/main` at
  `0086f97fab1e63ab1644367e1b3c6376138ea111`
- Current-main reconciliation: merged Azure `origin/main`
  `43d415cfb50717d94b69c07d7be648a12691f1f8` after Slate Studio Slice 1
  released
- Status: **Pass** at reviewed source
  `45a3e494283fc55c767e9786180eb823395551f1`; Azure release remains

## Purpose

Make one visual-creation rule durable across Codex and Claude without adding a
duplicate design or review chain:

1. ChatGPT creates every new or materially revised PeerSlate production-intent
   concept, mockup, storyboard, responsive/state set, style exploration, and
   image; existing Pete-locked authorities remain valid until materially
   revised.
2. Pete selects and locks the exact durable authority.
3. Codex or Claude implements the locked authority and captures real evidence.
4. An implementer or reviewer may identify a visual, truth, usability, or
   accessibility defect and make documented non-material adaptations for
   semantic structure, focus, contrast, touch targets, reduced motion, truthful
   state wiring, or text reflow, but may not originate or substitute the visual
   design.
5. A material change to composition, hierarchy, dominant object/action,
   typography family, color language, or responsive interaction model returns
   to ChatGPT and Pete for a revised exact lock before implementation continues.

Browser screenshots and bounded parity critique remain implementation/review
evidence, not competing visual creation.

## Model and role boundary

The current architect, implementer, and reviewer choices for Codex and Claude
remain centralized in `docs/AI_MODEL_AND_ROLE_ROUTING.md`. The
production-intent visual portion of either route comes exclusively from
ChatGPT; this package intentionally does not duplicate mutable model versions.

## Writable files

- `AGENTS.md`
- `CLAUDE.md`
- `docs/AI_WORKFLOW.md`
- `docs/AI_MODEL_AND_ROLE_ROUTING.md`
- `docs/governance/OWNER_VISUAL_INTEGRITY_STANDARD.md`
- `docs/governance/DECISIONS.md`
- `docs/governance/AI_DELIVERY_AUDIT_REGISTER.md` for the normal Slice 1
  runtime-closeout increment
- `docs/governance/CURRENT_BASELINE.yaml`,
  `docs/governance/CURRENT_STATE.md`, and
  `docs/governance/ACTIVE_INITIATIVES.md` only to reconcile the already
  released Slice 1 present-tense state
- `docs/initiatives/PS-SLATE-STUDIO-SLICE-1-001/OWNER_TECHNICAL_COMPLETION_REPORT.md`
  only for its exact post-release evidence
- this initiative directory
- directly relevant governance guardrail tests

## Exclusions

No runtime route, template, stylesheet, image authority, product package,
Bible, Roadmap, baseline pointer, feature flag, schema, deployment
configuration, or production behavior changes here. This package records who
creates future visuals; it does not create the Slate Studio Slice 2 visual set.

## Acceptance criteria

1. The shared, Claude-specific, workflow, routing, visual-standard, and decision
   records all state the same ChatGPT-only visual-creation boundary.
2. Codex and Claude implementation/review roles remain available without
   visual-authority creation rights.
3. A visual change has one return path rather than an improvised or competing
   design pass.
4. Focused governance/site-rule tests and `git diff --check` pass.
5. One fresh exact-SHA reviewer checks the changed policy for ambiguity,
   contradiction, and unnecessary ceremony before release.
6. The already released Slice 1 increments the central runtime-slice counter
   once, without triggering a duplicate audit.
