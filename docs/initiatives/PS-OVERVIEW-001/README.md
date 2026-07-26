# PS-OVERVIEW-001 — Member Overview direction and self-service contract

**Status:** Documentation-only direction package complete and ready for owner
inventory review. It is not runtime implementation authorization and does not
lock either supplied concept as production visual authority.

**Owner:** Pete.

**Designated session manager:** The current Pete-authorized Codex task for this
package.

**Sole documentation writer:** Codex on
`work/2026-07-25-overview-direction-001`.

**Authoritative base:** Azure DevOps `origin/main` at
`598cb7d7a5f067564ce3e00540352176decd2b8b`.

**Reserved files:** `docs/initiatives/PS-OVERVIEW-001/**` only.

**Forbidden files and domains:** Runtime code, routes, templates, styles,
JavaScript, APIs, databases, migrations, feature flags, deployment
configuration, shared governance pointers, current résumé records, Story,
Journal, Studio, Home, Community, and every other initiative package.

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
- The current résumé uses a right-side section ribbon. Its first entry is
  **Overview** when an Overview is published and **Summary** when the fallback
  Summary renders. The approved future left Context Rail remains a separately
  gated migration; either contextual control stays outside the center canvas.
- The public Ask [Name] AI and Résumé PDF actions remain truthful page-level
  capabilities and must receive one nonduplicative approved placement when the
  Summary is absorbed.
- The concepts' top navigation, internal left-looking column, and footer are not
  a new navigation system.
- All Overview content belongs to the same center canvas. A style may use
  columns at wide viewports, but no content block is treated as the permanent
  site rail.
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
- [Completion and handoff report](OWNER_TECHNICAL_COMPLETION_REPORT.md) records
  the documentation result and its evidence limits.

## Durable source inputs

| Source | Package copy | SHA-256 | Status |
| --- | --- | --- | --- |
| Owner-supplied Portfolio Overview | `source/story-and-career-owner-concept-2026-07-25.png` | `0F2F70EB8AB4E417CE6F2A0CEB3F47BC00C7EEAD9BFFC78A9B6C6D3D081613C4` | Direction input; not visual authority |
| Owner-supplied Business Overview | `source/work-and-impact-owner-concept-2026-07-25.png` | `B5276B1728B80A17BE395DD4F1ABBB9BEC74346AEF8D928E9CC8DFA7B59412E6` | Direction input; not visual authority |
| Claude requirements draft supplied by Pete | `source/claude-overview-system-requirements-draft-2026-07-25.txt` | `09E026EAE767CF0B21F262F9D2236E5ABE360631162FAF049AE7D6219979DD43` | Consulted input; reconciled by this package |

The local download and attachment paths are intentionally not authoritative.
The package copies and hashes are the durable cross-computer references.

## Authority and release boundary

This package records requirements and owner direction only. It adds no route,
schema, migration, API, flag, template, visual asset for runtime use, or
member-facing capability. The existing public résumé and Story remain
unchanged.

The supplied concepts are not exact implementation screenshots. ChatGPT must
create the production-intent visual/state set from the owner-approved inventory,
and Pete must lock exact durable files and hashes before architecture or runtime
implementation begins.

Because the future system includes audience/publication and consequential AI
boundaries, an activated implementation package will require a fresh
independent review against its exact branch, SHA, and evidence.

## Next gate

Pete reviews the inventory and the small set of owner decisions in
[the style and visual gate](05_STYLE_MANIFESTS_AND_VISUAL_GATE.md). After that
approval, ChatGPT creates the complete Story & Career and Work & Impact visual
authority set, including sparse, long-content, editing, visitor-preview, mobile,
large-text, and failure states. No implementation begins until Pete locks those
exact files and a separate bounded implementation package is activated.
