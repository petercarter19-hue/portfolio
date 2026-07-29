# PS-INTERVIEW-FOCUS-UI-001 Production Evidence

Date: 2026-07-29

## Decision

**Production Gate F: Pass.**

The approved Interview Focus implementation squash-merged, deployed through
the automatic main pipeline, and passed independent live desktop/mobile
verification.

## Release chain

- Pre-change base and rollback SHA:
  `a85ffbc93a1def86f99db66df26702a59aff4cbc`
- Retained Azure rollback branch:
  `backup/2026-07-28-pre-interview-focus-ui-001-a85ffbc9`
- Reviewed source:
  `da6f93946adf4f3ba3c29d39362b71b0946501a7`
- Frozen runtime:
  `0b2d5ffa6aac56dbb6736bbeb5cee13c8baffeb7`
- Azure PR: 201
- Squash merge:
  `b8e9e26ba0e8cb2bc93fa936c4ddd7985e9f72fb`
- Automatic production pipeline: 279 (`20260729.3`)
- Production artifact: `279.zip`
- Artifact SHA-256:
  `5494b661511095adf6b7ea3060c16e3faa967db88dfc846a7e6e230a5c27b54a`
- Exact production release:
  `453e0bee3f0322e0e06e1481`

Pipeline 279 passed Build, Deploy, and ProductionSmoke for the exact squash
merge. Candidate stages skipped, as required for a production main run.

A fallback run, pipeline 280 (`20260729.4`), was queued against the same exact
merge while the automatic run was late to appear in the listing API. It was
canceled before it started and performed no release work. It is not a
production failure.

## Independent live checks

Public route checks returned the expected results:

| Route | Result |
|---|---|
| `/healthz` | 200, `Cache-Control: no-store`, exact release matched |
| `/` | 200 |
| `/interview-studio` | 200 |
| `/robots.txt` | 200 |
| `/sitemap.xml` | 200 |

The HTML responses retained the expected must-revalidate/no-cache behavior,
CSP, and HSTS.

Browser verification passed at 1440 x 900 and 390 x 844:

- the current Interview Studio title and route marker were present;
- the initial desktop answer field measured 144 px and the mobile field
  measured 160 px;
- a 5,000-character live fill grew the desktop field to 825 px;
- the grown field had no internal clipping or scrollbar and reset to 144 px
  when emptied;
- the question queue was nonmodal on desktop and a native modal on mobile;
- Escape restored focus to the visible queue opener in both layouts;
- neither viewport had horizontal overflow;
- route-specific Ask Pete access remained present while the overlapping global
  floating launcher remained hidden; and
- the captured live screens matched the approved focused hierarchy and compact
  field behavior.

## Exact asset-byte proof

The live versioned assets matched the squash merge byte-for-byte:

| Asset | Live query | Bytes | SHA-256 |
|---|---|---:|---|
| `interview-studio.css` | `v=da6cbd709f9c` | 102031 | `da6cbd709f9c6c16c3041343aff7ed6b235e94f8488f3b303c78307e0eb82bac` |
| `interview-studio.js` | `v=a252e9b0b277` | 117664 | `a252e9b0b2772eaa9e4356485cabf744990196e6ab36bdd17ca14946d9315bf6` |

## Disposition

- The remote runtime task branch was verified exact and deleted.
- The pre-change Azure rollback branch remains retained.
- The temporary Candidate Web App and separate B1 plan were removed.
- The production App Service remains running on its original plan.
- No Claude reference, attribution, branch record, or handoff was removed.
- No new art was required; ChatGPT image generation was not invoked.
- Historical `PS-HOME-INTERVIEW-PARITY-001` remains closed.
- Current Focus homepage visual parity remains open under
  `PS-HOME-INTERVIEW-FOCUS-PARITY-001`.
- Gate Launch was not expanded or separately assessed for this bounded public
  refinement.
- Gate Operate's 24-72-hour follow-up remains pending.

This record describes the tree-changing product release. A later
documentation-only governance closeout may receive a newer main commit and
release identity while retaining these exact Interview runtime bytes.
