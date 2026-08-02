# Implementation handoff — sole runtime writer

## Objective

Implement `PS-INTERVIEW-STUDIO-VISUAL-FACELIFT-001` exactly on
`work/2026-08-01-interview-studio-visual-facelift-001`, based on the package
commit supplied by the manager.

This is implementation, not architecture or design exploration. Preserve the
released Interview Studio state machine and apply the locked visual authority.

## Start gate

1. Confirm the assigned worktree is clean and its HEAD is the exact package
   commit supplied by the manager.
2. Read `START_HERE.md`, `CURRENT_BASELINE.yaml`, `AI_WORKFLOW.md`, this package
   README, manifest, parity matrix, the released
   `PS-INTERVIEW-FOCUS-UI-001` README, and its V3 functionality/AI/Video/all-mode
   contracts.
3. Verify the 12 PNG dimensions and SHA-256 values against the manifest.
4. Inventory the current template/CSS/JavaScript hooks and tests before editing.
5. Stop for any collision, missing authority, hash mismatch, required backend or
   shared-shell change, or material visual decision not resolved by the package.

## Implementation rules

- Work only in the assigned implementation worktree and branch.
- Preserve all data attributes, form ownership, semantic labels, event targets,
  request shapes, local-storage keys, media cleanup, and state transitions.
- Implement the Studio-local header in `interview_studio.html` and
  `interview-studio.css`; do not edit `base.html` or shared navigation files.
- Use existing destination variables exactly as mapped in the package.
- Use one DOM for light/dark. Theme changes tokens and atmosphere only.
- Do not manufacture controls or data to make a screenshot look complete.
- Do not use a raster background containing UI. Build the interface from real
  semantic HTML/CSS; background architecture may use CSS gradients/shapes or a
  package-local decorative asset if genuinely necessary and documented.
- Preserve and test every unpictured released state.
- Make narrow truth/accessibility/reflow adaptations when required and record
  them. Stop before a material design substitution.

## Verification and evidence

- Run focused Interview tests, JavaScript parse checks, and the wider suite
  justified by any shared behavior touched.
- Run the route locally and capture real browser screenshots at the 12 locked
  1536×1024 states, plus representative 390×844 and Video 844×390 states.
- Compare real screenshots side by side with the locked PNGs and correct visible
  drift.
- Verify keyboard/focus, 200% zoom/reflow, reduced motion, long content,
  permission/failure recovery, theme state retention, network media locality,
  and storage truth.
- Self-review the complete diff and fill the package completion report.

## Handoff boundary

Commit the complete implementation and evidence on the implementation branch.
Return exact base/final SHAs, changed files, test/evidence results, documented
adaptations, unresolved findings, and an explicit handback to the manager.

Do not push, create a PR, merge, deploy, alter production, or claim Pete's final
browser acceptance.
