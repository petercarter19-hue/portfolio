# Measured Visual Evidence

## Evidence state

- Candidate: Work & Impact fidelity implementation plus shared 15-percent
  center-width amendment
- Source branch:
  `work/2026-07-28-overview-work-impact-fidelity-001`
- Source base:
  `544a3db245035f1f64bfcd2cb12fb524c0615a55`
- Accepted implementation source:
  `36241e12f70884d240f66c65c264c4fab0afafee`
- Local base URL: `http://127.0.0.1:5022`
- Work route:
  `/petec/resume?overviewStyle=work-impact`
- Story regression route:
  `/petec/resume?overviewStyle=story-career`
- Browser: headless Google Chrome at device scale factor 1
- Page scale: normal CSS layout; no page-level zoom or transform fitting
- Visual owner acceptance: approved by Pete on 2026-07-28
- Independent review: complete; no unresolved implementation or visual finding
- Homepage assessment: complete; no homepage file or product projection changed
- Merge / deployment / production verification: not started

## Authority

The Work & Impact comparison authority is:

`docs/initiatives/PS-OVERVIEW-001/visual-authority/generated-direction/work-and-impact-rich-desktop-2026-07-26.png`

- Dimensions: 886 × 1776
- SHA-256:
  `959F39E741ABC9438891487C031A8093759422FF6266F288E9AAD44CFE86A538`
- Depicted state: rich, business-first Work & Impact Overview above the detailed
  résumé

The source raster is an editorial direction board rather than literal browser
geometry. The final shell follows the locked three-region architecture: member
and résumé-section navigation on the left, dominant Overview / résumé center,
and contextual Ask Pete AI on the right.

## Capture tool and evidence location

The repeatable capture tool is:

`docs/initiatives/PS-OVERVIEW-001/work-impact-fidelity/tools/capture_evidence.mjs`

The tool opens the public style URLs, requires HTTP `200`,
requires exactly one Overview with the requested `data-style-id`, waits for
fonts, records `getBoundingClientRect()` geometry, requires zero document-level
horizontal overflow, requires proof-value containment, requires every Work
presentation image to be complete with non-zero natural dimensions, requires
the correct desktop or mobile selector to be visible, verifies both selector
instances mark the requested style, and then captures normal viewport
screenshots.

Current output:

`output/playwright/work-impact-style-switch-final/`

Authoritative measurements for this evidence pass:

`output/playwright/work-impact-style-switch-final/measurements.json`

The file was generated at `2026-07-28T19:12:17.066Z`.

## Owner-directed 15-percent width amendment

Pete directed that the center content be widened by about 15 percent for both
Overview styles. The implementation uses exact cap arithmetic:

| Region | Prior wide value | Revised wide value | Change |
|---|---:|---:|---:|
| Left rail | 160px | 160px | none |
| Center stage | 960px | 1,104px | +144px / +15% |
| Right AI rail | 320px | 320px | none |
| Two gaps | 64px | 64px | none |
| Maximum shell | 1,504px | 1,648px | +144px |

At 1,920px and 2,560px viewports, both Story & Career and Work & Impact resolve
to the same 1,104px center. At 1,440px the shell uses the available space and
the center resolves to 864px, preserving both rails without overflow rather
than forcing the wide cap.

## Responsive geometry

| Evidence case | Shell | Center | Overview root | Rail state | Horizontal overflow |
|---|---:|---:|---:|---|---:|
| Work & Impact, 2560×1440 | 1,648px | 1,104px | 1,104px | both docked | 0px |
| Story & Career, 2560×1440 | 1,648px | 1,104px | 1,104px | both docked | 0px |
| Work & Impact, 1920×1080 | 1,648px | 1,104px | 1,104px | both docked | 0px |
| Story & Career, 1920×1080 | 1,648px | 1,104px | 1,104px | both docked | 0px |
| Work & Impact, 1440×900 | 1,408px | 864px | 864px | both docked | 0px |
| Story & Career, 1440×900 | 1,408px | 864px | 864px | both docked | 0px |
| Work & Impact, 390×844 | 390px | 390px | 366px | compact local row | 0px |
| Story & Career, 390×844 | 390px | 390px | 366px | compact local row | 0px |
| Work & Impact, 320×844 | 320px | 320px | 296px | compact local row | 0px |

The measured Overview and center edges agree at the desktop cases. At mobile,
the 12px page inset intentionally produces the 366px and 296px Overview cards.

## Style-selector geometry

| Evidence case | Visible selector | Size | Active label |
|---|---|---:|---|
| Desktop, 1440 / 1920 / 2560 | left context rail | 134px × 112.31px | requested style |
| Mobile, 390 | above Overview | 366px × 53.19px | requested style |
| Mobile, 320 | above Overview | 296px × 53.19px | Work & Impact |

Both selector instances remain in the document for consistent semantics, but
only the breakpoint-appropriate instance is visible. Every capture verified
that both instances expose the same `aria-current` style and that the visible
selector occupies no center-stage width on desktop.

## Work & Impact composition measurements

At both 1,920×1,080 and 2,560×1,440:

| Region | Measurement |
|---|---:|
| Overview root | 1,104px wide |
| Hero | 1,102px × 300px |
| Hero supporting copy | 11.84px font / 17.76px line height |
| Proof strip | 1,102px × 70.39px |
| Main business body | 1,102px × 1,097.48px |
| Closing invitation | 1,102px × 96px |

At 1,440×900, the hero and proof-strip heights remain 300px and 70.39px while
their widths reflow to 862px. At 390×844, desktop fixed-height constraints are
released: the hero becomes 692.14px, the proof strip becomes 179.19px, and the
body becomes 3,947.25px in one readable flow. At 320×844 the Work hero becomes
724px, the proof strip remains 179.19px, and the body becomes 4,110.27px. None
of those cases clips the page horizontally.

All four proof values were contained inside their cards at every captured Work
viewport:

- `30+`
- `9 / $19.2M`
- `$36M+`
- `35%`

## Screenshot inventory

The final local evidence folder contains:

- `work-impact-2560x1440.png`
- `work-impact-1920x1080.png`
- `work-impact-1920x1080-full-page.png`
- `work-impact-1440x900.png`
- `work-impact-390x844.png`
- `work-impact-320x844.png`
- `story-career-2560x1440.png`
- `story-career-1920x1080.png`
- `story-career-1920x1080-full-page.png`
- `story-career-1440x900.png`
- `story-career-390x844.png`
- `measurements.json`

The Story & Career captures are regression evidence for the shared width
amendment. They are not a second visual-acceptance claim.

## Truth-preserving implementation adaptations

1. The runtime candidate uses finite public profile records instead of treating
   illustrative mockup claims as reusable product logic.
2. The Work & Impact presentation overlay is package-local at
   `docs/initiatives/PS-OVERVIEW-001/work-impact-fidelity/fixtures/work-impact-publication.json`.
   The public static résumé JSON contains no Work & Impact draft.
3. The Work hero, systems diagram, leadership meeting, sustainment aircraft,
   and data dashboard images are package-local fixtures under
   `docs/initiatives/PS-OVERVIEW-001/work-impact-fidelity/fixtures/assets/`
   with stored truth labels:
   - AI-extended presentation derivative of Pete's public profile photo;
   - AI-generated illustrative systems-engineering diagram;
   - AI-generated presentation derivative of Pete's public profile photo;
   - AI-generated illustrative sustainment scene; and
   - AI-generated illustrative engineering dashboard.
4. The five assets are published under `static/images/overview/` because Work &
   Impact is now a visitor-selectable presentation. The overlay remains
   server-side and references only those fixed, known asset paths.
5. Each generated image carries a compact visible **AI-assisted visual** or
   **AI-generated visual** badge. Its full truth label remains available to
   assistive technology.
6. Those assets are not documentary proof of work, employment, teams, programs,
   outcomes, or personal relationships.
7. The desktop hero and proof strip release their fixed heights on mobile to
   preserve text and action reflow.
8. The contextual AI remains in the right rail, while the left rail contains
   member context and in-page résumé destinations only.
9. The 1,104px wide center is a direct owner amendment after the earlier 960px
   live-fidelity release. It changes both styles symmetrically.
10. Internal projection errors return `500`. A selected public Work projection
    failure falls back to the published default Story & Career projection
    rather than emitting a broken or partially trusted view.

## Compact typography exception

The original final architecture requires primary body copy of at least 16 CSS
pixels at normal scale. The locked Work & Impact raster and the owner-accepted
Story & Career live-fidelity precedent instead use a deliberately compact
editorial/business type system. The current Work candidate follows that
precedent; for example, its measured wide-desktop hero supporting copy is
11.84px with a 17.76px line height.

This is a documented authority conflict, not an invisible implementation
detail. Pete's 2026-07-28 approval of the rendered candidate accepts this
style-specific exception. Automated tests and geometry evidence did not waive
the architecture's 16px requirement; the owner decision closed it.

## Current mismatch register

| Item | Status | Required closure |
|---|---|---|
| Work & Impact real-browser visual fidelity | Complete | Pete approved the rendered candidate on 2026-07-28 |
| Compact typography versus 16px architecture minimum | Accepted exception | Pete's 2026-07-28 approval accepts the rendered style-specific type |
| Full repository regression suite | Complete | Current-main run: `1055 passed, 3 skipped, 0 failed` |
| Homepage parity | Complete | `GET /` returned `200`, length `73133`, with canonical `/petec/resume` link present; no homepage file or projection changed |
| Independent complete-diff / accessibility review | Complete | No unresolved implementation or visual finding |
| Merge, pipeline, and production | Not started | Requires accepted source, Azure PR, squash merge, deploy, and live verification |

The visual mismatch register is empty. This is final visual evidence, but it is
not yet a merge, deployment, or production claim.

## Verification limit

The focused Overview and résumé suite passed with `81 passed` and one existing
Flask-Limiter in-memory warning.

The final configured repository suite passed with `1055 passed`, `3 skipped`,
and `0 failed` in `57.88s` pytest time (`58.7s` wall time).
It produced 19 non-failing warnings: one existing Flask-Limiter
in-memory-storage warning and 18 Pillow deprecation warnings.

## Homepage assessment

The final candidate does not modify a homepage file or homepage product
projection. A logged-out local `GET /` returned `200` with response length
`73133`, and the response retained the canonical `/petec/resume` link.
The local public résumé candidate exposes both styles through the on-page
selector. This branch is not yet merged or deployed.

The independent review is complete. It found no remaining implementation,
geometry, responsive, privacy, homepage, test, or accessibility issue requiring
code correction. Pete then approved the rendered candidate and directed
deployment on 2026-07-28.

## Publication trust-boundary evidence

- The presentation overlay resides under
  `docs/initiatives/PS-OVERVIEW-001/work-impact-fidelity/fixtures/`; the public
  runtime does not expose that JSON file.
- `static/data/resume_data.json` contains no Work & Impact presentation draft.
- The five selected presentation images are fixed assets under
  `static/images/overview/` and load successfully as WebP files.
- The removed internal media route is no longer part of the runtime.
- Internal Work & Impact projection errors return `500` without a Story &
  Career fallback.
- Missing or invalid public style values return the Story & Career default.
- The capture tool requires the requested style, correct selector state,
  successful response, zero overflow, contained proof values, and fully loaded
  media before recording an evidence case.

These measurements prove the recorded local browser geometry and overflow
state. They do not prove owner visual acceptance, merge, deployment, production
identity, real-member validation, every failure state, or every WCAG 2.2 AA
manual check.
