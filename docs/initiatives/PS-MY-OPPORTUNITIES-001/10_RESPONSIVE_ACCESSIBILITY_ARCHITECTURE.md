# 10 — Responsive and accessibility component architecture

One semantic system, three compositions. The same DOM reflows across desktop
(1600×1200 proof target), iPad landscape (1024×768), and mobile (390×844) —
no viewport-specific DOM duplication that can drift (V4 architecture brief
rule, preserved). Visual character (warm ivory, near-black ink, restrained
forest/gold/terracotta, editorial type) follows the approved authority set;
the desktop/iPad search-band geometry is quarantined pending Pete's corrected
artifacts (doc 15 §2) — component *semantics* below are stable either way.

## 1. Component inventory (semantic contract)

| Component | Semantics | Key behavior |
|---|---|---|
| Search band row 1 | One labeled search input (natural language) | AI-native; no separate AI mode; submit reachable by keyboard; Enter submits |
| Search band row 2 | Compact control band: interpreted criteria chips, verification-scope selector, `Edit criteria`, `All filters` | Exactly two rows at every supported viewport; mobile collapses chips to `<primary> +N` with full editing behind `Edit criteria` |
| Criteria chip | Button (edit affordance), text label | Never icon-only meaning; removal/edit keyboard-operable |
| Clarification sheet | Modal dialog (`role="dialog"`, labelled) | Initial focus on question; focus contained; Escape/close returns focus to invoker; **nothing preselected**; Apply disabled until selection; background results remain unchanged (doc 03 §3) |
| Results rail (desktop/iPad) / results list (mobile) | Complementary landmark; list semantics; result count heading | Restrained width; rail does not widen with viewport; footer down-arrow navigation outside cards (preserved V2 direction); count is real, never invented |
| Result card | Article with heading (near-black title), facts, qualification summary, save control | Selected state visible and programmatically exposed (`aria-current`) |
| Dossier (selected role) | Main content; anchor nav: Role overview, Qualifications, Practical fit, Responsibilities, Company & source | Anchors are real in-page navigation (skip-friendly); dossier continues below the fold — content is never shrunk to fit |
| Selected-role header | Company mark/name, title, actions: Save, `Review in Opportunity Slate`, View original posting (external-link affordance permitted here only) | Governing copy is exactly `Review in Opportunity Slate` |
| Qualification row | Term/status/basis structure; one evidence drawer open at a time; ≤2 strongest confirmed items surfaced, more acknowledged | Status text + icon (never icon-only); reason copy from the doc 07 §4 alias table |
| Evidence drawer | Disclosure pattern (`aria-expanded`) | In-place expand; keyboard toggle; View / Correct-or-add evidence actions |
| State banners (posting changed, closed by source, could not reverify, reduced coverage, evidence boundary) | Status region at dossier top | Distinct copy per state; never color-only; actions per doc 03 |
| Loading stages | Live region (`aria-live="polite"`, additive announcements) | Meaningful stages; copy bound to accepted retrieval topology (doc 16); no invented counts |
| Saved list | List with per-item verification + lifecycle overlays; local search/filter controls (doc 03 §7) | Mixed states visible; undo affordance after removal with accessible confirmation |
| Save confirmation | Non-modal toast + inline state change; `Saved for later` | Announced via live region; Undo focusable; never opens/creates a Slate |
| Slate first-use confirmation | Modal dialog | Private-workspace explanation before creation; explicit confirm/cancel |

## 2. Responsive composition rules

- Desktop: two-pane (dominant dossier left, restrained rail ~340–380px right,
  24–32px gap); content continues below 1200px viewport height.
- iPad landscape: same two-pane contained at 1024×768; no third control row;
  no control stacking that changes the interaction model.
- Mobile 390×844: true reflow, single column; decision content (title, gate
  status, trust explanations) precedes routine metadata; dense information
  moves below, never disappears from the full page; 44px-class touch targets;
  no horizontal overflow at any approved state.
- Breakpoint behavior is container-driven where practical, so embedded reuse
  cannot silently break composition.

## 3. WCAG 2.2 AA obligations (C8 gate matrix)

- **Keyboard**: every search, chip, filter, scope, clarification, result,
  anchor, drawer, save, undo, Slate, and evidence action operable; visible
  focus; logical order matching visual order (v2's mobile focus-order lesson);
  no keyboard trap outside modal containment.
- **Structure**: landmarks (banner/nav/main/complementary), one h1, ordered
  heading levels, list/table semantics for facts, labeled form controls.
- **Dialogs/sheets**: proper dialog semantics, initial focus, containment,
  Escape, focus return (clarification and Slate confirmation both).
- **Live regions**: search progress, save/undo confirmations, assessment
  refresh — polite, non-spammy; failure banners use assertive only for
  blocking failures.
- **Contrast**: AA for text, controls, focus indicators, and status colors on
  the warm palette (contrast-checked tokens; measured adjustments documented
  as non-material adaptations under the visual standard).
- **Zoom/reflow**: 200% zoom and 320px-equivalent reflow with no loss of
  content or function (v2's 200%-equivalent proof is the convention).
- **Reduced motion**: `prefers-reduced-motion` honored for stage transitions,
  sheet animation, toast entry.
- **Forced colors**: status conveyed by text/structure survives
  forced-colors mode; focus/selection borders remain visible.
- **Icons never the only signal**; external-link icons only on View original
  posting (never on evidence controls — preserved V2 rule).

## 4. Truth-in-rendering rules

Fixture data is labeled as fixture in every rendering context; nothing claims
live provider data before Level 3 evidence exists. Every state renders from
real backing state (doc 16 traceability); demo/loading/unavailable/denied are
distinct surfaces, never approximated by one generic error.

## 5. Long-content and internationalization floors

Long titles/requirement clauses wrap (no ellipsis-only truncation of trust
copy); bounded fields render fully in the dossier; date/number rendering per
doc 04 §7; copy avoids concatenation-built sentences so later localization
does not break truth labels.

## 6. Visual-authority gaps vs functional contracts (not permission to invent)

The approved set lacks: a mobile fully-verified selected-role dossier
artifact, and non-mobile adaptations of mobile-only failure/dialog states.
These are **visual-authority** gaps only. The corresponding *functional*
contracts are fully defined and not deferred: the fully-verified selected
mobile state is specified in doc 16 §1 and must be implemented and
functionally proven by C8 at 390×844 like every other state.

The quarantine reserves visual composition to Original ChatGPT + Pete under
the visual standard — it does not waive, defer, or weaken the
functional/mobile contract. C8's completion therefore separates two gates:

1. **Functional gate (never waived):** functional, accessibility, and
   failure-state proof of every state at every supported viewport, including
   fully-verified selected mobile.
2. **Visual gate:** Pete-locked authority and parity for the missing
   artifacts before visual acceptance/merge of those compositions.

No writer invents an unapproved layout to close the visual half
(R3/05B floor, preserved).
