# PS-OVERVIEW-PUBLIC-INTEGRATION-001

## Status and authority

**Status:** Complete, released, and verified live on 2026-07-26 through Azure
PR 187, squash merge `2f03a514b3329d27c49dcd1e7515a181827c2597`,
and automatic pipeline 254.

**Owner / deployment authority:** Pete.

**Designated session manager and sole writer:** The current Pete-authorized
Codex task.

**Owner authorization:** On 2026-07-26 Pete explicitly overruled the earlier
staged-publication hold and directed the new Overview to replace the public
opening now, be visible at `/petec/resume`, and be released through production.
Pete then clarified that the detailed résumé must fit below the Overview while
the Career Constellation may remain as large as it is.

**Authoritative base:** Azure DevOps `origin/main` at
`6907e9e08bf76ed2051265c6855fcbf64c47c228`.

**Branch:** `work/2026-07-26-overview-public-integration-001`.

**Controlling visual and product authority:**

- `../10_VISUAL_AUTHORITY_LOCK_2026-07-26.md`
- `../11_FINAL_ARCHITECTURE_CONTRACT_2026-07-26.md`
- `../09_OWNER_DECISIONS_2026-07-26.md`
- `../implementation-slice-1/README.md`

This package implements the already locked Story & Career public direction. It
does not create or materially revise visual authority.

## Exact activated outcome

At the canonical public route `/petec/resume`:

1. a published Story & Career Overview replaces and absorbs the existing
   Summary opening;
2. the Overview is built only from Pete's existing approved public résumé and
   Story data plus an explicit profile-owned public projection selection;
3. the system-owned **Résumé begins here** boundary leads directly into the
   retained detailed résumé;
4. the retained order remains **Impact, Skills, Experience, Credentials**;
5. the detailed résumé reflows at normal CSS scale inside the dominant center
   stage, with no CSS `zoom` or transform fitting;
6. the final left local-section Context Rail replaces the weaker right-side
   section ribbon;
7. one persistent public **Ask Pete AI** surface occupies the right contextual
   rail on sufficiently wide screens and collapses to the established compact
   Ask action when space is constrained;
8. the existing Career Constellation remains after Credentials at its current
   large/full-width presentation; and
9. existing `#summary` and `#resume-overview` bookmarks resolve to the new
   Overview opening, while detailed-section anchors remain stable.

The owner’s latest Constellation direction in this package supersedes the
center-fit sentence in
`../implementation-slice-1/DOWNSTREAM_PUBLIC_INTEGRATION_HANDOFF.md`. The
historical Slice 1 handoff is not rewritten after merge.

## Capability truth and deferred behavior

This is an immediate public activation of Pete's current approved projection.
It is not the member composer, draft store, publication-history system,
unpublish workflow, or AI proposal workflow described by later architecture
slices. Those member-authoring and persistence capabilities remain deferred.

The shared renderer remains generic. Profile-specific content and selection
live in profile-owned structured data; shared rendering logic may not hardcode
Pete, his employers, dates, credentials, metrics, media, or Story wording.

No schema, database, migration, external service, feature flag, or new
authorization boundary is introduced. The existing allowlisted public-profile
loader remains the retrieval boundary. Public Ask AI continues to use the
existing approved-public-evidence endpoint.

## Reserved files

- `app.py`
- `overview_projection_service.py`
- `static/data/resume_data.json`
- `templates/resume2.html`
- `templates/partials/member_overview.html`
- `static/css/member-overview.css`
- `static/css/resume2.css`
- `static/js/living-resume-v2.js`
- `tests/test_resume2.py`
- `tests/test_member_overview_public_integration.py`
- `tests/test_overview_projection_service.py`
- `docs/initiatives/PS-OVERVIEW-001/public-integration-slice/**`

Unrelated runtime, data, templates, styles, scripts, governance pointers,
deployment configuration, other initiative packages, and the Career
Constellation partial/implementation are not reserved.

## Implementation boundary

- Add a generic public-projection adapter over one already-loaded public
  profile. It must fail closed on invalid or cross-owner references.
- Keep the generic fixture preview route and all Slice 1 fixtures truthful and
  unchanged.
- Add a profile-owned publication selection to the existing public résumé data.
  Exact proof values are copied without AI inference, calculation, rounding,
  embellishment, or mutation and render without provenance/verification
  fields.
- Reuse the semantic Overview partial. Public embedding must not duplicate
  document IDs used by the retained résumé.
- Remove the old Summary markup only when a ready public projection exists.
  The reusable template retains a truthful Summary fallback for profiles
  without one.
- Keep Connect and View résumé in the Overview hero, Résumé PDF once in the
  left rail, and Ask Pete AI once in the right contextual rail. Existing
  detailed-section contextual Ask buttons may continue to open that one shared
  assistant.
- Do not alter the Career Constellation include, its content, or its interaction
  implementation.

## Required validation and evidence

- focused projection and public-route tests;
- existing Overview renderer/accessibility tests;
- existing résumé and shared Career Constellation tests;
- full configured repository suite;
- HTML semantic/ID/action-count checks;
- keyboard, focus, reduced-motion, no-JavaScript, and 200-percent zoom checks;
- responsive geometry at 390 × 844 and full-browser 1440 × 900, 1920 × 1080,
  2560 × 1440, and 3840 × 2160;
- no horizontal overflow and normal-scale `zoom: 1` / `transform: none` on the
  Overview and retained center fitting chain;
- compare-refine evidence against the Pete-locked Story & Career and
  shared-rail authority;
- homepage product-projection parity assessment;
- complete-diff self-review;
- Azure pull request, required squash merge, exact pipeline and deployment
  verification; and
- production verification of the canonical route, stable anchors, detailed
  section order, public Ask boundary, and full-width Constellation.

Public publication and visual work normally require a fresh independent review.
The current runtime does not provide a separate reviewer lane inside this task;
the release may not silently represent that review as completed. Repository
policy checks, complete-diff self-review, automated tests, owner direction, and
production verification remain required, and the completion report must label
the independent-review status truthfully.

## Stop conditions

Stop rather than improvise if the implementation would:

- expose generic/Maya fixture content publicly;
- invent or materially rewrite Pete's public claims;
- render Overview and Summary as two openings;
- delete or reorder the retained detailed résumé;
- reduce, center-fit, or otherwise alter the Career Constellation;
- duplicate Overview/detailed-section IDs or primary shared actions;
- rely on CSS zoom or transforms to make the retained résumé fit;
- add persistence, publication history, composer, AI-proposal, or unpublish
  behavior without a separately activated package; or
- bypass the Azure pull-request and deployment path.
