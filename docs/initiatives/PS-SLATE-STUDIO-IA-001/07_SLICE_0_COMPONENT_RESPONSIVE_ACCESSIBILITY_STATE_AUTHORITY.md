# PS-SLATE-STUDIO-IA-001 — Slice 0 component, responsive, accessibility, and state authority

**Date:** 2026-07-23. **Author:** Codex at Pete's direction.
**Status:** **SLICE 0 DIRECTION AUTHORITY AND OWNER VISUAL REVIEW COMPLETE -
runtime activation is not granted.**

This document extends, but does not redraw, the exact owner-locked desktop
light/dark files in document 04. It defines the component grammar and
adaptation rules needed to mock and judge Slice 1. It is not implementation or
runtime evidence.

## 1. Fixed authority

The exact desktop files remain:

- `visual-authority/build-your-future-dark-owner-approved-2026-07-23.jpg`
  — SHA-256
  `9481EF994D3B0A7967E38E8BB502D05865EF09657BC35986B85CF4844B71C7BB`;
- `visual-authority/build-your-future-light-owner-approved-2026-07-23.jpg`
  — SHA-256
  `973942E876427CDDEEAE6AAF966DA1997D56EA1647D1DBC67151C8DAAE0579A6`.

The hierarchy, Board scale, selected-work relationship, theme equivalence, and
professional finish are locked. The faint Board curves are **selected-item or
explicit show-connections state only**. Default, loading, empty, permission,
and unavailable states show no relationship curves.

## 2. Component inventory

| Component | Required role | Slice 1 behavior |
|---|---|---|
| Skip link | Bypass repeated global and Studio navigation | Real, first focusable control |
| Signed-in global header | Brand, My Slate, Slate Studio, Community, account, theme | Server-rendered; no hardcoded person; no fake search |
| Studio navigation | Workshop, Build Your Future, Interview Studio | One current item; public/browser-local disclosure on Interview handoff |
| Page introduction | Slate Studio eyebrow, `Build Your Future`, short promise | Matches locked hierarchy; one `h1` |
| Sandbox explanation | Explains private experimentation and member control | Visible, concise, not tooltip-only |
| Workspace status | Current private state | Slice 1 says `Studio workspace — private`; it does not claim a saved draft exists |
| Published Slate action | View exact currently published Slate | Real server-supplied link, or honest no-published-Slate state |
| Workspace stage | Dominant Board-shaped region | Truthful empty, loading, or unavailable frame; no invented Board cards |
| Stage state message | Names condition, consequence, and next safe action | Persistent text, not color/icon alone |
| Reserved selected-work region | Future detail hierarchy | Not rendered as fake content in Slice 1 |
| Reserved directions region | Future creative directions | May show a restrained, noninteractive `Coming later` explanation; no active experiment cards |
| Truth footer | Sandbox promise, private default, no automatic save/place/publish | Visible at the end of the stage |
| Alert/recovery region | Route or stage errors and retry | Programmatically announced; focus moves only on user-triggered navigation/retry |

The following locked-image controls are **not active Slice 1 components**:
Arrange, Board persistence, Add note, Upload, Voice, Type, Edit, Connect
evidence, Use in my Slate, Practice in Interview Studio with grounding,
Explore another direction, Ask Slate, and publishing controls. Omit them or
label the whole future region `Coming later`; do not render enabled-looking
controls that do nothing.

## 3. Theme authority

Light and dark are two themes of the same semantic document, component tree,
routes, states, focus order, and capability set.

- Theme switching must not reset navigation, workspace state, or focus.
- Light and dark use the same information hierarchy and content density.
- Status cannot rely on blue/gold/green/red alone.
- Text and functional icons meet WCAG 2.2 AA contrast; working text does not
  use handwriting as its only typeface.
- Forced-colors keeps headings, links, controls, current navigation, borders,
  and focus visible.
- User theme preference may be remembered only through the existing approved
  theme mechanism; Slice 1 creates no private content persistence.

## 4. Responsive authority

### Wide desktop (approximately 1200 CSS px and above)

- Preserve the locked silhouette: global header, Studio navigation, two-column
  intro/status band, dominant Board-shaped stage, restrained lower region.
- The stage has a readable maximum line length and does not stretch working
  text edge to edge.
- If the stage is unavailable or empty, retain its visual dominance without
  simulating cards, notes, counts, or connections.

### Desktop / small laptop (approximately 900–1199 CSS px)

- Keep the intro and status in two columns only while both remain readable.
- Studio navigation remains one labeled navigation row.
- Stage controls and state messages wrap without overlap.

### Tablet (approximately 768–899 CSS px)

- Intro and status stack in semantic order.
- The Board-shaped stage uses available width.
- Global and Studio navigation remain distinct; no third rail or bottom bar.
- Touch targets are at least 44 by 44 CSS px where controls exist.

### Mobile (390 CSS px reference)

- Order: skip link, global header, Studio navigation, page identity,
  sandbox/private status, published state/action, workspace state, truth
  footer.
- Studio navigation may horizontally scroll as one labeled row only when all
  items remain keyboard reachable and the current item is visible on load.
- No tiny spatial Board. Slice 1 shows one readable structured workspace
  region; later Board slices provide grouped Work / Projects / Short Term /
  Long Term regions.
- No sticky layer may cover the `h1`, status, alert, or focused control.

### Narrow mobile (320 CSS px)

- Long labels wrap or the Studio navigation scrolls without clipping.
- The account and theme controls remain reachable.
- Status text and published action stack; icons never replace text.
- No horizontal page scroll at 100% or 200% zoom.

### Mobile landscape / short height

- Global and Studio navigation are not simultaneously sticky.
- Skip-to-content and normal document scroll reach the workspace immediately.
- Dialogs are not required for Slice 1.

### 200% zoom / reflow

- Use the narrow single-column composition at an effective 640 CSS px.
- No two-dimensional Board miniature, clipped tab, or off-screen recovery
  action is permitted.
- Text can grow without overlapping decorative frame treatments.

## 5. Accessibility authority

### Structure and naming

- One `h1`: `Build Your Future`.
- Global navigation and `Slate Studio sections` have distinct accessible
  names.
- The dominant stage is a labeled `section` or `region`; state copy is
  associated with its heading.
- Status uses text plus an optional decorative icon.
- Current navigation uses `aria-current="page"`.
- The published link's accessible name identifies the member's Slate without
  hardcoding Pete.

### Keyboard and focus

Focus order follows visual/reading order. There is no focusable disabled-looking
control and no positive `tabindex`.

1. skip link;
2. global navigation and account/theme controls;
3. Studio navigation;
4. published Slate link when real;
5. retry or safe next action when present; and
6. ordinary footer links.

Visible focus is at least as clear as the locked gold/blue active language in
both themes and survives forced-colors. Route navigation places focus at the
new `h1`; an in-place retry moves focus to the resulting state heading only
after the member initiated the retry.

### Screen reader and live regions

- Server-rendered states require no announcement on initial load.
- A real client-side retry/loading transition may use
  `aria-live="polite"` and `aria-busy` on the stage only.
- Permission or complete unavailability is not hidden behind generic
  "something went wrong" text.
- Decorative frame, texture, curve, clip, paper, and chalk treatments are
  hidden from assistive technology.

### Motion

- Slice 1 requires no motion to understand state or navigation.
- Under `prefers-reduced-motion: reduce`, theme, focus, navigation, and state
  changes are immediate.
- Relationship curves have no Slice 1 animation because they do not appear.

### Language and cognitive clarity

- Every state says what is true, what did not happen, and what the member can
  safely do.
- No score, urgency, streak, progress percentage, or engagement count appears.
- `Coming later` is used only for an intentionally visible unavailable
  capability; absent controls are preferred when the label adds no value.

## 6. State authority

| State | Required presentation | Forbidden implication |
|---|---|---|
| Ready frame | Private status, real published state, dominant workspace frame | That Board data, editing, or saving is connected |
| Loading | Shell and navigation remain usable; stage names what is loading; real navigation/retry only | Decorative spinner on a fully server-rendered page or fake delay |
| Empty | `No supported work is connected here yet` only when a server contract has authoritatively returned zero supported references | Treating unavailable integration, a fixture gap, or failed request as member emptiness |
| Permission denied | No private payload; explain that this protected workspace is not available to the current session and offer sign-in or safe return as applicable | Client-side hiding, another member's identity, or resource existence |
| Unauthenticated | Existing protected-route sign-in redirect with safe same-origin return | Rendering a private shell before authentication |
| Unavailable | Private shell may remain, but no member content is fabricated; explain temporary unavailability and provide real retry/navigation | Falling back to Pete fixture data or calling the state empty |
| Published Slate available | Real canonical link and current published wording/status from the server | Preview, publication, freshness, or audience claims not supported by the contract |
| No published Slate | `No published Slate yet`; no dead link | That the private workspace is missing or that the member must publish |
| Long content | Member name/status/state wrap; stage and navigation remain intact | Ellipsis that removes identity, privacy, or recovery meaning |
| No JavaScript | Navigation, private/published truth, unavailable/empty state, and safe links work server-rendered | JS-only ownership, permission, or state determination |

### Empty versus unavailable admission rule

An implementation may show the empty state only after a server-owned,
authorized Slice 1 contract explicitly returns a successful zero-supported-item
result. If Slice 1 has no such contract, it must show **unavailable / not
connected yet**, not empty. A visual test harness may render all named states
for review, but fixtures may never be admitted as member-path production
evidence.

## 7. Selected-item relationship rule

The relationship curves have exactly three legitimate states:

1. **Default/unselected:** absent.
2. **Selected item or explicit show connections:** faint, bounded to the
   selected relationships, secondary to selection accent and matching title.
3. **Selection cleared / state changed / mobile structured view:** absent.

Curves never form a permanent crosshair, workflow, hierarchy, score, prediction,
or connector to the detail panel. They are decorative enhancement over a
semantic relationship list that later slices must provide.

## 8. Slice 0 owner visual evidence

Pete accepted the responsive and state direction set preserved in
`visual-authority/slice-1/`. Its exact dimensions, SHA-256 hashes, state copy,
and evidence limits are recorded in
`visual-authority/slice-1/ASSET_MANIFEST.md` and package document 10.

The set covers:

- light/dark desktop, tablet, 390 px, 320 px, and short-landscape direction;
- narrow/200% reflow direction with a visible focused link;
- forced-colors direction;
- ready/not-connected, loading, admitted-empty, permission-denied,
  unavailable/recovery, published-link, and no-published-Slate direction; and
- component, wording, and theme parity with the original locked hierarchy.

Static raster direction cannot prove runtime behavior. Before Slice 1 release,
the implementation package must still return real evidence for exact CSS
viewports, 200% browser reflow, no horizontal page scrolling, keyboard order
and focus, screen-reader naming/order, WCAG contrast, touch targets,
forced-colors, reduced-motion, no-JavaScript, long member/localized content,
two-member isolation, safe unauthenticated redirect, server-owned state
admission, and recovery behavior.

Designated-manager receipt also remains a D6 activation condition. This
document and the accepted raster set do not activate runtime work.
