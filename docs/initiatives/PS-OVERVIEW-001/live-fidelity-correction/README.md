# PS-OVERVIEW-LIVE-FIDELITY-CORRECTION-001

## Status

- State: Owner-accepted local correction; release in progress
- Owner: Pete Carter
- Writer: Codex
- Original implementation base: Azure DevOps `origin/main` at
  `f85747275b81359c0d99bd99f340e65aa58420b8`
- Release integration base: Azure DevOps `origin/main` at
  `49072ef2af7c3268bc06ee5e51c9133b9b33c259`
- Branch: `work/2026-07-27-overview-live-fidelity-correction-001`
- Route: `/petec/resume`

## Problem

Pete withdrew visual acceptance of the published Overview on 2026-07-27 after
comparing the live route with the locked Overview mockups. The public
integration is structurally functional, but its center-stage scale, density,
section composition, and visitor AI rail do not match the approved visual
authority closely enough.

## Authority

This is a fidelity correction, not a new visual direction. The controlling
authorities remain:

- `../10_VISUAL_AUTHORITY_LOCK_2026-07-26.md`
- `../11_FINAL_ARCHITECTURE_CONTRACT_2026-07-26.md`
- `../08_WIDE_DESKTOP_WIDTH_AMENDMENT.md`
- `../visual-authority/generated-direction/story-and-career-rich-desktop-2026-07-26.png`
- `../visual-authority/generated-direction/story-and-career-narrow-desktop-2026-07-26.png`
- `../visual-authority/generated-direction/story-and-career-mobile-standard-390x844-2026-07-26.png`
- `../visual-authority/generated-direction/ask-pete-ai-overview-open-desktop-2026-07-26.png`

## Scope

1. Correct the published Story & Career center composition to the locked visual
   hierarchy and proportions.
2. Keep the left résumé-section rail and contextual public AI rail sticky on
   wide desktop; undock them before the center becomes cramped.
3. Recompose narrow desktop and mobile without CSS zoom or transform fitting.
4. Preserve real public member content, source boundaries, section anchors,
   AI behavior, and the detailed résumé below the Overview.
5. Preserve the Career Constellation and all unrelated résumé behavior.
6. Add focused regression tests and durable viewport evidence.

## Reserved files

- `templates/resume2.html`
- `templates/partials/member_overview.html`
- `static/css/member-overview.css`
- `static/css/resume2.css`
- `static/data/resume_data.json` only if an authority-preserving projection
  correction is required
- focused Overview and résumé integration tests
- this package and its evidence artifacts

## Exclusions

- no new Overview style;
- no member editor implementation;
- no canonical résumé or Story rewrite;
- no database, migration, identity, or authorization change;
- no Career Constellation redesign;
- no direct push to `main`;
- no release claim without pipeline and live evidence.

## Acceptance

- The approved mockup is re-opened during every compare-refine pass.
- Desktop evidence covers at least 1440x900, 1920x1080, 2560x1440, and
  3840x2160 CSS pixels.
- Responsive evidence covers the approved narrow-desktop and 390x844 mobile
  compositions.
- The mismatch register is empty except for documented content-truth,
  accessibility, or responsive adaptations.
- Pete provides final visual acceptance before merge.

## Local correction result

The corrected implementation now uses a real, centered three-region desktop
shell at normal browser scale:

- 160px résumé section rail;
- responsive center stage capped at 960px;
- 320px public AI rail;
- 32px inter-region gaps;
- 1504px maximum shell width.

The public AI rail remains docked through common 1366px and 1440px desktop
widths. It undocks at 1312px, before the center becomes too narrow. The left
section rail remains available through 1024px. At 960px and below, the rails
become the compact member / Overview / Sections row. At 390px the opening
stacks into the approved portrait, identity, action, and 2x2 proof sequence.

The wide desktop left rail contains member context and in-page resume section
navigation only. The contextual public AI assistant remains in the right rail,
avoiding the redundant left-side Ask action Pete removed during final review.

Measured results and the final evidence inventory are recorded in
[`MEASURED_VISUAL_EVIDENCE.md`](MEASURED_VISUAL_EVIDENCE.md).

## Current gate

Pete accepted the corrected real build on 2026-07-28 and authorized release.
The correction is not yet committed, merged, deployed, or verified live. The
next gate is release integration against current Azure `origin/main`, followed
by the required tests, Azure pull request, deployment, and live verification.
