# PS-OVERVIEW-001 — Member Overview direction and self-service contract

**Status:** Final product and logical implementation architecture complete.
Pete approved the page-purpose inventory, first-release product decisions,
Story & Career and Work & Impact public directions, sparse/narrow/mobile
treatments, editor states, consolidated left résumé-section rail, contextual
right AI rail, and Review & Publish treatment on 2026-07-26. The controlling
architecture is
`11_FINAL_ARCHITECTURE_CONTRACT_2026-07-26.md`. Exact approved visual files and
superseded generation history are recorded in
`10_VISUAL_AUTHORITY_LOCK_2026-07-26.md`. This package still does not implement
or change the public résumé.

**Owner:** Pete.

**Designated session manager:** The current Pete-authorized Codex task for this
package.

**Sole package writer:** Codex on the recorded direction/amendment lanes and
the current package-local
`work/2026-07-26-overview-visual-authority-001` lane.

**Initial authoritative base:** Azure DevOps `origin/main` at
`598cb7d7a5f067564ce3e00540352176decd2b8b`.

**Wide-desktop amendment base:** Azure DevOps `origin/main` at
`52128a57c81969788c9dde68636d26c0ebd6a7db`.

**Owner-decision amendment base:** Azure DevOps `origin/main` at
`e915b173ec4a2c14ea6d499f45416335a6b93b29`.

**Visual-authority branch base:** Azure DevOps `origin/main` at
`9d01fa7315115599bae0b45c237b72b265ac24e8`.

**Visual-authority branch:** `work/2026-07-26-overview-visual-authority-001`.

**Reserved files:** `docs/initiatives/PS-OVERVIEW-001/**` only.

**Forbidden files and domains:** Runtime code, routes, templates, styles,
JavaScript, APIs, databases, migrations, feature flags, deployment
configuration, shared governance pointers, current résumé records, Story,
Journal, Studio, Home, Community, and every other initiative package.

**Wide-desktop amendment:** Pete's 2026-07-25 monitor-width review is captured
in [Wide-desktop canvas and evidence amendment](08_WIDE_DESKTOP_WIDTH_AMENDMENT.md).
The direction PNGs are tall editorial boards, not browser-shaped viewport
specifications. A future Overview must occupy the full resolved résumé content
column and may not be placed inside another arbitrary narrow stage.

## Owner direction captured

PeerSlate will have **one Member Overview system** with two coherent
presentation styles over the same member-approved content:

1. **Story & Career** — the flagship and recommended starting style. It combines
   professional proof with career arc, selected Story, values, and personality.
2. **Work & Impact** — a concise, results-forward alternate style emphasizing
   capabilities, outcomes, and professional fit.

The member publishes one Overview at one stable public location. Visitors do
not receive a style toggle in the first release. Changing style is a private
draft operation and does not change the public Overview until the member
explicitly publishes the whole revision.

The Overview is a curated projection over canonical résumé, Slate, and
eligible public Story records. It is not a second résumé, a competing truth
store, or a freeform web-page builder.

Optional first-release proof metrics are bounded authored Overview claims:
members supply the exact values, AI cannot invent or alter them, and no metric
source-backing or provenance system is included. Source-backed metrics are
deferred until after the basic experience is working and reviewed live.

## Placement and page boundary

- The Overview renders above the member's actual résumé.
- On the current `/petec/resume` acceptance fixture, a published Overview
  **absorbs and replaces the existing Summary opening**—portrait, identity,
  headline, introduction, and opening actions—rather than rendering another
  hero above it. When no Overview is published, the current Summary remains the
  truthful fallback.
- The concepts' illustrated **Full Résumé** summaries are excluded. The
  Overview ends at a system-owned **Résumé begins here** boundary, after which
  the detailed Impact, Skills, Experience, and Credentials résumé sections
  start.
- The public-integration slice replaces the current weaker right-side section
  ribbon with the approved left Context Rail. It contains the member identity,
  Overview/Summary, Impact, Skills, Experience, Credentials, and one separated
  Résumé PDF action. It never repeats route-level My Story, Work, Slate Board,
  Community, or Interview Studio navigation.
- The right region is a distinct contextual AI rail: public **Ask [Name] AI**
  uses approved public information only; private **Ask Slate AI** uses only
  authenticated, authorized workspace context. It is not section navigation.
- The hero uses Connect as its primary action and View résumé as its
  same-page secondary action. Public Download PDF and Ask [Name] AI remain
  truthful shared contextual capabilities outside the hero. Each action
  appears once; mobile may use one compact accessible shared-actions menu.
- The concepts' internal content columns and footer are not a new navigation
  system. The final shared-shell interpretation is the left local-section rail,
  dominant center stage, and right contextual AI rail.
- All Overview content belongs to the same center canvas. A style may use
  columns at wide viewports, but no content block is treated as the permanent
  site rail.
- The Overview root fills the resolved center stage. The earlier
  `min(92vw, 90rem)` amendment remains the starting center-stage candidate when
  the shell has sufficient space. With both rails docked, the center resolves
  from available width; the AI rail undocks before the center becomes cramped.
  Monitor inches never determine the breakpoint.
- Wide bands, media, and count-aware grids may use that canvas. Readable text
  measure is controlled inside each block instead of narrowing the entire
  Overview.
- The future Overview is not fitted with CSS `zoom` or `transform` scaling.
  The current résumé's desktop `zoom: 0.9` is documented as present-state
  evidence, not inherited target behavior.
- Skills appears before Education, Certifications, and Awards. The member-facing
  name is **Skills**, not **Core Tools**.

## Product principle

> The member controls content, visibility, order, emphasis, media, and a
> truthful destination. PeerSlate controls geometry, typography, spacing,
> count-aware reflow, responsive behavior, and accessibility.

This keeps manual editing complete and useful without requiring AI or a
developer, while preventing arbitrary placement, fixed empty slots, illegible
type, and layouts that work for only one person's content.

## Package map

- [Source register and decision log](00_SOURCE_REGISTER_AND_DECISION_LOG.md)
  identifies the exact owner concepts and reconciles the supplied Claude draft.
- [Owner direction and product contract](01_OWNER_DIRECTION_AND_PRODUCT_CONTRACT.md)
  defines the one-system/two-style model, truth boundary, and scope.
- [Page-purpose and non-redundancy inventory](02_PAGE_PURPOSE_AND_NON_REDUNDANCY_INVENTORY.md)
  accounts for every meaningful Overview item before visual creation.
- [Block, content, destination, and reflow contract](03_BLOCK_CONTENT_DESTINATION_AND_REFLOW_CONTRACT.md)
  defines the finite block library, public content budgets, sparse states, and
  no-gap behavior.
- [Editor, AI, publication, and trust contract](04_EDITOR_AI_PUBLICATION_AND_TRUST_CONTRACT.md)
  defines the manual workflow, optional AI proposals, authorization, versioning,
  privacy, and failure behavior.
- [Style manifests and visual gate](05_STYLE_MANIFESTS_AND_VISUAL_GATE.md)
  defines what the styles share, what may differ, and the exact next visual
  acceptance step.
- [Implementation information and acceptance plan](06_IMPLEMENTATION_INFORMATION_AND_ACCEPTANCE_PLAN.md)
  gives a future writer the conceptual records, render rules, delivery slices,
  and test matrix without authorizing code.
- [Cross-computer handoff](07_CROSS_COMPUTER_HANDOFF.md) gives the next session
  a bounded restart path.
- [Wide-desktop canvas and evidence amendment](08_WIDE_DESKTOP_WIDTH_AMENDMENT.md)
  records the 27-/32-inch-monitor concern as CSS-viewport requirements,
  current-shell reference geometry, and exact visual/implementation evidence.
- [Owner decisions — 2026-07-26](09_OWNER_DECISIONS_2026-07-26.md) records
  Pete's inventory approval, first-release audience and metric rules, public
  density, style names, action placement, and starting wide geometry.
- [Visual authority selection and lock — 2026-07-26](10_VISUAL_AUTHORITY_LOCK_2026-07-26.md)
  names the exact composite authority, hashes, interpretation, truth labels,
  geometry, and homepage impact.
- [Final Overview architecture contract — 2026-07-26](11_FINAL_ARCHITECTURE_CONTRACT_2026-07-26.md)
  is the controlling product/logical architecture for page composition,
  section and AI rails, responsive behavior, records, services, editor,
  publication, failure recovery, implementation slices, and supersession.
- [`visual-authority/`](visual-authority/) contains the exact generated
  standard-state files, image-generation record, responsive editable
  interpretation, state/geometry contract, and measured evidence.
- [Slice 1 implementation package](implementation-slice-1/README.md) activates
  a separate generic read-model/renderer foundation after this visual package
  is merged; it does not authorize runtime work on this visual branch.
- [Completion and handoff report](OWNER_TECHNICAL_COMPLETION_REPORT.md) records
  the documentation result and its evidence limits.

## Durable source inputs

| Source | Package copy | SHA-256 | Status |
| --- | --- | --- | --- |
| Owner-supplied Portfolio Overview | `source/story-and-career-owner-concept-2026-07-25.png` | `0F2F70EB8AB4E417CE6F2A0CEB3F47BC00C7EEAD9BFFC78A9B6C6D3D081613C4` | Direction input; not visual authority |
| Owner-supplied Business Overview | `source/work-and-impact-owner-concept-2026-07-25.png` | `B5276B1728B80A17BE395DD4F1ABBB9BEC74346AEF8D928E9CC8DFA7B59412E6` | Direction input; not visual authority |
| Claude requirements draft supplied by Pete | `source/claude-overview-system-requirements-draft-2026-07-25.txt` | `09E026EAE767CF0B21F262F9D2236E5ABE360631162FAF049AE7D6219979DD43` | Consulted input; reconciled by this package |
| Story & Career rich desktop | `visual-authority/generated-direction/story-and-career-rich-desktop-2026-07-26.png` | `E4DFDB298DF3EEB706F3ACDB5955E546E526F9B3D0F42475A67B1BF3DD37E1B2` | Owner-approved flagship rich direction |
| Work & Impact rich desktop | `visual-authority/generated-direction/work-and-impact-rich-desktop-2026-07-26.png` | `959F39E741ABC9438891487C031A8093759422FF6266F288E9AAD44CFE86A538` | Owner-approved alternate rich direction |
| Story & Career narrow desktop | `visual-authority/generated-direction/story-and-career-narrow-desktop-2026-07-26.png` | `081445064CEAC73A47A94450B9E023216AA5D5118238DE373E7DD9FD97CF7BC8` | Owner-approved responsive reference |
| Work & Impact narrow desktop | `visual-authority/generated-direction/work-and-impact-narrow-desktop-2026-07-26.png` | `052E70263114DCC5C6D701BEAC14F66A36C9B37B98ACD0D427A92F618CD60606` | Owner-selected responsive reference |
| Corrected mobile proof-point editor | `visual-authority/generated-direction/overview-editor-proof-point-mobile-390x844-2026-07-26.png` | `123C50D65685F49C392C6EBC5E3163A10FFEB380CCC5C4384D3774B87FC1F6A6` | Owner-approved mobile editor authority |
| Consolidated rails and public Ask AI | `visual-authority/generated-direction/ask-pete-ai-overview-open-desktop-2026-07-26.png` | `B9D884F34D1CBD9E1C02E69F2CB243043C7883CA28C9993379083444E379F831` | Owner-approved shell/context direction |
| Review and publish | `visual-authority/generated-direction/overview-review-publish-desktop-2026-07-26.png` | `6305581DF81514E80EA74CA167819918CBD16CECA87F0C265B027D8A9081CB93` | Owner-approved publication-review direction |

The local download and attachment paths are intentionally not authoritative.
The package copies and hashes are the durable cross-computer references.

## Authority and release boundary

This package records requirements, owner direction, and production-intent
visual authority only. It adds no route, schema, migration, API, flag, runtime
template, runtime asset, or member-facing capability. The existing public
résumé and Story remain unchanged.

The owner-supplied source concepts remain direction provenance. The approved
rich, sparse, narrow, mobile, editor, rails, AI-context, and publication-review
references plus the package contracts form the composite authority. The early
generated `*-wide-standard*` pair is superseded generation history and does not
control implementation. None of these files is a screenshot of implemented or
live behavior.

Because the future system includes audience/publication and consequential AI
boundaries, an activated implementation package will require a fresh
independent review against its exact branch, SHA, and evidence.

## Next gate

The architecture and visual lock are complete, including Pete's explicit
approval of the corrected mobile proof-point editor. Finish package-local
visual/source/hash validation and complete-diff self-review, then merge this
documentation/design package through Azure.

After that merge, start
`PS-OVERVIEW-SLICE-1-001` on its own branch from the new current
`origin/main`. Slice 1 is limited to a generic projection service, semantic
renderer, fixtures, and internal review route. The existing public résumé
remains unchanged, and the member Overview remains unavailable until later
composer, publication, public-integration, acceptance, and release packages
are separately completed.
