# PS-OVERVIEW-SLICE-1-001 — Generic projection and renderer foundation

## 1. Status and activation

**Status:** Activated for a separate implementation branch after the
`PS-OVERVIEW-001` visual-authority package is merged to current Azure
`origin/main`.

Pete reviewed the two style directions and directed the team to move forward
on 2026-07-26. That instruction activates this bounded first implementation
slice. It does not authorize the later composer, persistence, publication,
public-route integration, AI service, schema, migration, homepage change,
deployment enablement, or production claim.

## 2. Owner, manager, and writer

- **Owner:** Pete.
- **Designated session manager:** the current Pete-authorized Codex task until
  an exact repository handoff names a replacement.
- **Implementation writer:** Codex on a new short-lived branch created from the
  visual-authority squash merge.
- **Planned branch:** `work/2026-07-26-overview-slice1-renderer-001`.
- **Required base:** the then-current fetched Azure `origin/main`, containing
  the exact locked visual-authority package.
- **Delivery model:** self-managed bounded writer with complete-diff
  self-review and package evidence.

The visual-authority branch must not also become the runtime branch.

## 3. Purpose

Prove that one generic, deterministic Overview projection can render both
locked presentation styles for multiple fixture profiles and all fundamental
count-aware states without changing the public résumé.

This slice produces:

1. a finite, versioned block/style contract;
2. a pure projection/read-model builder;
3. generic fixture profiles;
4. a localhost/internal visual-review route;
5. semantic server-rendered output for Story & Career and Work & Impact;
6. deterministic sparse, standard, rich, missing-media, missing-proof,
   one-role, one-degree, and no-credential behavior;
7. exact geometry/accessibility evidence against the locked visual authority;
   and
8. a clear extension seam for the later owner composer and publication model.

It does not expose an editable or published member capability.

## 4. Current-code inspection

At visual-package base `9d01fa7315115599bae0b45c237b72b265ac24e8`:

- `/\<profile_slug\>/resume` is rendered through
  `_render_living_resume()` in `app.py`;
- public profiles are currently selected from the allowlisted
  `RESUME_PROFILE_FILES` fixture registry;
- `templates/resume2.html` contains the existing Summary opening, right-side
  ribbon, detailed Impact, Skills, Experience, and Credentials sections;
- `static/css/resume2.css` owns the current résumé composition and applies
  current desktop fitting that must not become the future Overview fit method;
- `static/js/living-resume-v2.js` owns current section-ribbon and detailed
  résumé interactions; and
- the current public route has no authenticated Overview draft/publication
  store.

The slice therefore uses an internal-only preview and new isolated renderer
assets. It does not pretend that multi-user publication exists.

## 5. Reserved runtime files

The implementation writer may create or edit only:

- `app.py` — add one localhost/internal review route and adapter call; no public
  route behavior change;
- `overview_projection_service.py` — new pure validation/projection module;
- `static/data/overview_fixtures.json` — new generic, explicitly illustrative
  renderer fixtures;
- `templates/overview_preview.html` — new internal review shell;
- `templates/partials/member_overview.html` — new semantic renderer partial;
- `static/css/member-overview.css` — new style manifests and responsive
  rendering;
- `static/js/member-overview-preview.js` — optional internal preview-state
  controls only; public meaning may not depend on it;
- `tests/test_member_overview_projection.py`;
- `tests/test_member_overview_renderer.py`;
- `tests/test_member_overview_accessibility.py`;
- `artifacts/ps-overview-slice-1-001/**` — implementation evidence; and
- `docs/initiatives/PS-OVERVIEW-001/implementation-slice-1/**` — package-local
  evidence and completion report.

If current-code inspection proves that a different exact file is necessary,
the writer stops and amends this package before touching it.

## 6. Forbidden files and domains

This slice may not change:

- the public `/\<profile_slug\>/resume` output or current Summary fallback;
- `templates/resume2.html`, `static/css/resume2.css`, or
  `static/js/living-resume-v2.js`;
- public profile data in `static/data/resume_data.json`;
- the shared shell, current ribbon, final future Context Rail, contextual AI
  rail, homepage, Story, Journal, Studio, Home, Community, Capture, Projects,
  or AI experience;
- authentication, identity, authorization, public audience, cache, or
  publication behavior;
- database schema, migrations, stored procedures, App Service settings,
  feature flags, external services, or deployment configuration;
- PDF generation or existing Ask [Name] AI behavior;
- shared governance pointers, Bible, Roadmap, or another initiative package;
  or
- any claim that the Overview is implemented for members, published, enabled,
  deployed, or live.

## 7. Data and truth contract

The read model is generic and serializable. It must distinguish:

- `record_linked`, `authored`, and `hybrid` block modes;
- style ID/version and block definition/version;
- member-approved display fields;
- semantic order, visibility, and approved emphasis;
- optional validated destination;
- eligible media reference plus focal/alt/truth label; and
- deterministic readiness/error state.

First-release proof claims contain only:

- exact member-supplied display value;
- short member-authored or accepted label;
- optional icon;
- optional public destination; and
- normal placement/order/visibility fields.

They contain no source, evidence, verification, confidence, or provenance-state
field. The service must reject any fixture attempting to add one.

No Pete-specific employer, role, date, metric, skill, degree, image, or story
may be required by the renderer.

## 8. Required generic fixtures

At minimum:

1. **early career:** one role, one degree, no proof, no awards, no images;
2. **career changer:** multiple roles, transferable skills, authored future
   direction, no public Story;
3. **experienced leader:** four authored proof claims, four roles, selected
   impacts, credentials, and eligible media;
4. **independent/creative:** work, skills, and Story emphasis without
   conventional corporate metrics; and
5. **text only:** no portrait or feature media.

Both styles must render every fixture. Pete remains an optional acceptance
fixture, never the reusable contract.

## 9. Render invariants

The implementation must:

1. emit exactly one identity hero;
2. omit empty/hidden/invalid blocks without a wrapper or gap;
3. render proof counts as: zero omitted, one feature, two pair, three equal
   group, four equal/count-aware group;
4. render one role as Career Focus rather than a fake timeline;
5. render one degree as confident Education rather than filler;
6. place Skills before Education, Certifications, and Awards;
7. preserve DOM, reading, keyboard, and default visual order;
8. use no masonry, fixed public text height, card scrollbar, clipped sentence,
   arbitrary custom HTML, or generic dead `More` action;
9. keep Connect primary and View résumé secondary in the hero;
10. represent Résumé PDF once in the final left local-section context and
    public Ask [Name] AI once in the right contextual-AI area of the internal
    preview without changing the real shared shell;
11. end at Résumé begins here without a duplicate résumé summary;
12. use the full resolved center column inside
    `min(92vw, 90rem)` at normal scale;
13. compute `zoom: 1` and `transform: none` throughout the fitting chain;
14. keep primary body copy at least 16 CSS pixels;
15. preserve approximately 55–70-character prose measures inside wide bands;
16. recompose to one semantic column on mobile and at large text; and
17. retain public meaning and real anchor destinations without JavaScript.

## 10. Internal preview contract

The new route is available only when:

- the request host is loopback (`127.0.0.1`, `localhost`, or `::1`); or
- the existing design-system preview environment switch explicitly permits an
  internal review route.

It must not accept a submitted owner ID, expose a draft API, persist changes,
publish content, or appear in global navigation. State/style controls are
clearly labeled fixture-review furniture and are excluded from the simulated
visitor representation when screenshots are captured.

## 11. Required tests

### Projection

- valid shared model renders in both styles;
- unsupported style/block/emphasis/version fails explicitly;
- invalid order, duplicate placement ID, over-budget collections, and unknown
  destination fail explicitly;
- proof claims reject source/evidence/verification/provenance fields;
- zero/one/many rules are deterministic;
- missing media and missing optional groups produce no empty output; and
- two fixture owners never share selected records or media identifiers.

### Route and public boundary

- internal route returns 200 on loopback;
- non-preview external host returns 404;
- current `/petec/resume` response remains byte/contract compatible for the
  asserted opening, ribbon, sections, Ask action, PDF, and aliases;
- current public route contains no internal fixture controls or new Overview
  draft state; and
- no new public mutation endpoint exists.

### Semantics and accessibility

- one `h1`, logical heading order, landmarks, and descriptive actions;
- style/state changes preserve semantic order;
- visible focus and keyboard operation for preview controls;
- mobile and 200-percent-equivalent reflow without two-dimensional scrolling;
- reduced motion has no essential dependency;
- images have correct meaningful/decorative treatment; and
- no public meaning depends on JavaScript.

### Visual and geometry

- exact named comparison with the applicable owner-approved rich, sparse,
  narrow, mobile, and final-shell references in
  `../10_VISUAL_AUTHORITY_LOCK_2026-07-26.md`;
- screenshots at 1440 × 900, 1920 × 1080, 2560 × 1440, 3840 × 2160,
  390 × 844, and representative intermediate/large-text states;
- Overview and resolved content-column edges differ by no more than two CSS
  pixels;
- no undocumented nested page-level max width;
- `zoom: 1`, `transform: none`, body copy at least 16 CSS pixels;
- no horizontal overflow; and
- sparse, standard, rich, text-only, missing-proof, one-role, one-degree, and
  no-credential comparisons.

## 12. Evidence and completion

The writer must return:

- exact fetched Azure base and final source SHA;
- complete diff and self-review;
- focused tests plus the configured repository suite required by risk;
- route-boundary and two-profile fixture evidence;
- named screenshot and measurement set;
- parity/deviation matrix against the locked composite authority;
- homepage-impact assessment: no homepage edit in this slice because the real
  member capability remains unavailable;
- standard completion report with plain-English outcome;
- `Pass`, `Conditional`, or `Fail` self-certification; and
- an exact next action.

## 13. Acceptance and release boundary

This slice may be accepted and merged as a renderer foundation without a
production-facing visual change only when:

- public résumé behavior is unchanged;
- the internal preview is truthful and access-limited;
- generic fixture and geometry evidence passes;
- no persistence/publication/AI capability is implied; and
- the completion report labels the member experience **unavailable**.

An automatic documentation/code pipeline after merge is evidence only for this
foundation. It is not proof that members can create or publish an Overview.
The later manual composer, publication/restore, AI proposal, public
integration, Context Rail migration, contextual AI rail, homepage parity, and
enablement slices require separate
activation and acceptance.

## 14. Stop conditions

Stop and return to the owner/manager if this slice would require:

- a database, migration, public draft/publication endpoint, or feature flag;
- editing the current public résumé template or behavior;
- hardcoding Pete fixture facts into renderer rules;
- a metric source/provenance system;
- arbitrary layout or user-authored HTML/CSS;
- a new shared navigation layer;
- material departure from the locked visual authority;
- another active writer's file; or
- a capability or live claim outside this package.
