# PS-OVERVIEW-WORK-IMPACT-FIDELITY-001

## Status

- State: Owner accepted; release in progress
- Owner: Pete Carter
- Writer: Codex
- Authoritative base: Azure DevOps `origin/main` at
  `544a3db245035f1f64bfcd2cb12fb524c0615a55`
- Branch: `work/2026-07-28-overview-work-impact-fidelity-001`
- Accepted implementation source:
  `36241e12f70884d240f66c65c264c4fab0afafee`
- Merge / deployment state: not merged and not deployed
- Visual acceptance: approved by Pete on 2026-07-28
- Public default: Story & Career remains the published Overview style

## Purpose

This package implements the locked **Work & Impact** business-first Overview as
a second finite presentation of the same public résumé information. It exposes
both Overview styles through a temporary on-page selector and applies Pete's
2026-07-28 direction to widen the center content by 15 percent for both Work &
Impact and Story & Career on sufficiently wide desktops.

This is a fidelity implementation, not new visual direction. It does not
replace the detailed résumé, add a second profile truth store, publish a style
change, or authorize a production release.

## Owner-authorized architecture exception

The 2026-07-26 final architecture deferred public visitor style switching and
listed a proposed public switcher as a stop condition. Pete explicitly changed
that decision on 2026-07-28: both styles must be available to users now through
an on-page switch, while durable user settings remain deferred. This package
records that bounded owner exception.

The exception authorizes only an allowlisted, URL-carried presentation choice
between `story-career` and `work-impact`. It does not authorize a second truth
store, account persistence, automatic publication, audience changes, arbitrary
styles, or AI-controlled selection.

## Visual and product authority

The controlling Work & Impact raster is:

- `../visual-authority/generated-direction/work-and-impact-rich-desktop-2026-07-26.png`
- Dimensions: 886 × 1776
- SHA-256:
  `959F39E741ABC9438891487C031A8093759422FF6266F288E9AAD44CFE86A538`

The exact hash was rechecked in this worktree. The controlling shared-shell and
behavior authorities remain:

- `../10_VISUAL_AUTHORITY_LOCK_2026-07-26.md`
- `../11_FINAL_ARCHITECTURE_CONTRACT_2026-07-26.md`
- `../08_WIDE_DESKTOP_WIDTH_AMENDMENT.md`
- `../visual-authority/generated-direction/ask-pete-ai-overview-open-desktop-2026-07-26.png`

Pete's later 2026-07-28 width direction is a measured implementation amendment:
the accepted wide-desktop center cap changes from 960 CSS pixels to 1,104 CSS
pixels, an exact 15-percent increase. It applies equally to the Story & Career
and Work & Impact center stages. It does not enlarge the rails or force a wide
layout into smaller viewports.

## Implemented local candidate

The accepted release candidate provides:

1. A Work & Impact public projection built from a finite, validated
   `work-impact-presentation.v1` profile-owned presentation.
2. A business-first hero, four-point proof strip, compact executive summary,
   career snapshot, skills and credential previews, seven bounded capability /
   impact / human-context modules, and one closing invitation.
3. The final shared three-region desktop shell:
   - 160px left member and résumé-section rail;
   - dominant center stage, capped at 1,104px on wide desktop;
   - 320px contextual Ask Pete AI rail;
   - two 32px gaps at the wide cap.
4. Mobile and intermediate reflow that removes fixed desktop-height constraints
   and avoids horizontal page scrolling.
5. A public on-page selector for the two styles:
   - `/petec/resume?overviewStyle=story-career`
   - `/petec/resume?overviewStyle=work-impact`
   - desktop places the selector in the left context rail;
   - mobile places a compact two-option selector immediately above the
     Overview.
6. Story & Career remains the default when no allowlisted style query is
   present. Invalid query values return the default Story & Career view.
7. A package-local Work & Impact publication overlay and five optimized public
   presentation assets under `static/images/overview/`. The public static
   résumé JSON still contains no Work & Impact draft or duplicate profile
   truth store.
8. A non-persistent selection contract: the selected style is encoded in the
   URL so it can be followed, bookmarked, or shared. Durable account settings
   and member preference persistence are explicitly deferred.

The selector is released behavior in this candidate, not an editor or a
publication workflow. It changes only the presentation used for the current
public request. It does not save to a member account, alter canonical profile
truth, or make an AI decision.

## Finite content and trust boundary

The Work & Impact projection accepts only bounded profile-owned fields:

- one hero and optional eligible hero media;
- one to four authored proof metrics;
- bounded executive-brief and career-snapshot lists;
- selected public skills, education, certifications, and awards;
- one to eight known section records;
- at most one outcomes section with at most four metrics; and
- one bounded closing invitation.

It rejects unknown fields, arbitrary HTML, unsupported section kinds, unsafe
section identifiers, unknown records, and non-public media. The Work & Impact
presentation overlay lives at:

`docs/initiatives/PS-OVERVIEW-001/work-impact-fidelity/fixtures/work-impact-publication.json`

The public `static/data/resume_data.json` contains no Work & Impact draft or
presentation overlay. AI-created media is presentation media, never evidence
of employment, team membership, program work, or outcomes.

## Presentation media

The local candidate uses five optimized WebP assets. Package fixture copies are
retained beside the publication overlay, and the public presentation uses the
corresponding files under `static/images/overview/`:

| Asset | Truth label |
|---|---|
| `static/images/overview/work-impact-hero-pete-ai-extended-2026-07-28.webp` | AI-extended presentation derivative of Pete's public profile photo |
| `static/images/overview/work-impact-systems-diagram-2026-07-28.webp` | AI-generated illustrative systems-engineering diagram |
| `static/images/overview/work-impact-leadership-meeting-2026-07-28.webp` | AI-generated presentation derivative of Pete's public profile photo |
| `static/images/overview/work-impact-sustainment-aircraft-2026-07-28.webp` | AI-generated illustrative sustainment scene |
| `static/images/overview/work-impact-data-ai-dashboard-2026-07-28.webp` | AI-generated illustrative engineering dashboard |

The truth labels are stored in the publication overlay. Every generated
visual now carries a compact visible **AI-assisted visual** or
**AI-generated visual** badge, while the complete truth label remains available
to assistive technology. These images are illustrative presentation derivatives
and must not be interpreted as documentary proof.

## Evidence

The durable capture tool for this package is:

`docs/initiatives/PS-OVERVIEW-001/work-impact-fidelity/tools/capture_evidence.mjs`

Its current output is:

`output/playwright/work-impact-style-switch-final/`

The measurements and screenshot inventory are documented in
[`MEASURED_VISUAL_EVIDENCE.md`](MEASURED_VISUAL_EVIDENCE.md).

Final verification after the public selector change includes:

- `81 passed` and one existing Flask-Limiter in-memory warning in the focused
  Overview and résumé suite;
- a completed independent review with no unresolved implementation finding
  beyond the two owner decisions below; and
- a logged-out homepage assessment: `GET /` returned `200`, the response length
  was `73133`, and the canonical `/petec/resume` link remained present. No
  homepage file or homepage product projection changed.

The final configured repository suite passed with
`1055 passed, 3 skipped, 0 failed` in `57.88s` pytest time (`58.7s` wall
time). The run produced 19 non-failing warnings: one existing Flask-Limiter
in-memory-storage warning and 18 Pillow deprecation warnings.

## Current gate

Pete approved the real-browser candidate and directed deployment on 2026-07-28.
That approval closes the visual mismatch register and accepts the rendered
style-specific compact typography documented in the evidence.

The remaining gate is release evidence: reconcile to current Azure `main`,
commit the accepted state, review it through an Azure DevOps pull request,
squash merge it, verify the exact deployment pipeline, and independently verify
both public styles live.
