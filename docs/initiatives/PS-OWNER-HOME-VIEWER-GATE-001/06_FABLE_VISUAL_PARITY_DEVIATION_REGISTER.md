# PS-OWNER-HOME-VIEWER-GATE-001 — Visual Parity and Deviation Register

Recorded 2026-07-19 by the Claude/Fable architecture writer. This register maps
every accepted visual area to its proposed implementation component and records
every known deviation. The implementation must **match or exceed** the accepted
authority (`01_FABLE_AUTHORITY_MANIFEST.md`); no silent deviations are
permitted. Architecture only — nothing here is implemented, deployed, or live.

## Controlling decisions

1. Binding baseline: `docs/governance/approved_owner_visual_baseline/01_owner_home_interface_mockup.png`.
2. Accepted working direction: authority candidate `31864e4`
   (`artifacts/ps-owner-home-viewer-gate-001/authority-candidate-31864e4/`).
3. **Owner decision 2026-07-19:** implement the dark cinematic shell, alpine
   atmosphere backgrounds, and overall look **exactly as the accepted candidate
   images show**. Pete explicitly overruled conflicting light-first-shell
   interpretations for this surface. Recorded here so no implementer or
   reviewer "corrects" the theme toward a light shell.
4. The candidate's route-scoped palette (Deep Navy `#071421`, Elevated Navy
   `#0D2133`, Cloud White `#FFFDF8`, Warm Ivory `#F5F0E7`, Paper `#FBF8F2`,
   Marigold `#D9AA2B`, text-safe dark gold `#8A5A00`, Focus `#FFD75E`, Success
   `#1E725F`, Error `#A43737`) is authority-derived and **route-scoped to Owner
   Home**. It does not modify the shared `--ps-*` Deep Navy Gold tokens in
   `static/css/style.css` or any other released surface.

## Area-by-area parity map

Component names refer to the frontend architecture
(`05_FABLE_FRONTEND_IMPLEMENTATION_ARCHITECTURE.md`). Authority exports refer
to `authority-candidate-31864e4/exports/`.

| # | Accepted visual area | Authority evidence | Proposed implementation component | Parity requirement |
|---|---|---|---|---|
| 1 | Cinematic navy shell with alpine atmosphere and navy/gold veils | exports 01–06, 23; `assets/owner-home-alpine-atmosphere.png` | `owner_home.html` page wrapper + `static/css/owner-home.css` background layers; exact accepted PNG served as the first-release source asset | Exact per owner decision; no regeneration, recrop, recolor, or substitution; no flat solid-navy fallback except `forced-colors`/no-image states |
| 2 | Owner area top band: PeerSlate wordmark, OWNER VIEW pill, Home current, Journal / My Slate / Connections / More **Coming later**, owner menu | exports 01, 02 | Page-scoped owner shell header partial (`templates/partials/owner_home/_owner_shell_header.html`); disabled nav items are non-interactive text with visible Coming later labels, zero routes | Same silhouette and order; genuinely disabled; complete public chrome suppressed only by the manager-approved standalone-shell conditional |
| 3 | Owner hero: avatar, "Welcome back, [name].", Owner Home · private workspace, truth line | exports 01–06 | `_owner_hero.html` partial fed by `owner-home.v1` `owner.display_name` | Variable identity; Newsreader serif welcome; never Pete-hardcoded |
| 4 | Dominant Capture action, upper-right (desktop) / directly under hero (mobile) | exports 01–06, 09 | `_capture_action.html` — a real `<a>` to the protected Capture route, gold-framed card | Only dominant active action; destination is the released `/app/capture` experience; unavailable state per contract |
| 5 | My Slate preview / audience rail: Owner View current-context segment + four disabled preview modes | exports 01–06 | `_audience_rail.html`; Owner View is text-state, the four modes are disabled capability previews from the server-owned availability registry | No requests, no routes, no sample projection; full visible **Coming later** wording |
| 6 | Luminous ivory working stage (Needs Review, Recent Moment, From your history) with unequal editorial hierarchy | exports 01, 02, 13 | `_stage.html` grid; per-category section components (`_review_list.html`, `_recent_moment.html`, `_resurfaced_moment.html`) | One continuous light stage inside the dark shell; hierarchy unequal (Review widest, Recent prominent media card, Resurfaced quieter) |
| 7 | Needs Review: max 3 rows + bounded-remainder shell row | exports 02, 19 | `_review_list.html`; rows from `review_items[]` (max 3); remainder affordance is shell context | Never a fourth record; empty state states there is nothing to review |
| 8 | Recent Moment card with media area and bounded summary | exports 01, 02 | `_recent_moment.html` | Real confirmed Moment only; media area uses abstract brand material until real Moment media exists (R3) |
| 9 | From your history (Resurfaced) | exports 01, 02 | `_resurfaced_moment.html`; first slice renders the **Coming later** dormant state until the deterministic policy ships | Never repeats the Recent item; no random filler |
| 10 | What PeerSlate noticed — dark insight surface | exports 01, 02 | `_noticed.html` dormant capability preview (dark card, gold-particle material, one-sentence purpose copy, **Coming later**) | No observation, count, recommendation, or generated output; slot is one of the nine objects |
| 11 | Connections — quiet relationship surface | exports 01, 02 | `_connections.html` dormant capability preview | No person, avatar, count, request, message, or activity |
| 12 | Your next useful step — warm gold surface with path-and-flag material | exports 01, 02 | `_next_step.html` from `next_step` object | Real deterministic action + truthful destination; single non-competing secondary action when it repeats Capture |
| 13 | Status/footer truth line | exports 01–06, 21 | `_home_status.html` | Concise truthful labels only (see R2) |
| 14 | Mobile 390 / 320 full-scroll composition with bottom nav (Home + Capture active; Journal/Slate/More Coming later) | exports 03–06, 23 | `owner-home.css` breakpoints + `_mobile_bottom_nav.html` (page-scoped, disabled future items) | Standalone reflow, no horizontal scroll, semantic order preserved; landscape 844 behaves per export 23 |
| 15 | Loading / empty / partial failure / complete failure / stale / restricted / recovery states | exports 12–18, 22 | State variants of the section components driven by the server view model + `owner-home.js` retry enhancement | Every state matches its export's composition and copy discipline |
| 16 | Visible focus (3px marigold + separation edge) | export 09 | `owner-home.css` `:focus-visible` rules | Meets WCAG 2.2 focus appearance on the dark shell and the ivory stage |
| 17 | High contrast / forced colors | export 10 | `@media (forced-colors: active)` block in `owner-home.css` (gap in current `owner-app.css` noted — Owner Home must ship its own) | Meaning survives in system colors; atmosphere may drop |
| 18 | Reduced motion | export 11 | `prefers-reduced-motion` block; static atmosphere | No motion required for meaning |
| 19 | 200% zoom / reflow | export 07 | Fluid `clamp()`/`min()` sizing, single-column reflow | No clipping/overlap at 200%; 320px reflow per export 05/06 plus R1 correction |
| 20 | Long content / bidi / missing media | export 08 | Wrapping rules + semantic media fallback | Bounded API text renders un-clipped; missing media keeps text alternative |

## Deviation register

Every deviation from the accepted candidate that implementation is authorized
to make. Anything not listed here requires Pete + designated-manager approval
before merge.

| ID | Deviation | Reason | Status |
|---|---|---|---|
| D1 (=R1) | 320px reflow of Noticed + Next Step corrected (stacked controls, no clipped grounding text, pills wrap to their own rows) | Accessibility/reflow defect in the candidate at 320px; correction improves the product | Owner-directed; record final screenshots at 320px |
| D2 (=R2) | Fixture/QA pills (TEST FIXTURE, PRIVATE FIXTURE · GENERIC DATE, FUTURE DESIGN FIXTURE banners, evidence notes) are removed from the real product; truthful state labels (Private draft, Coming later, Stale, Not published) remain, once per element | Those pills are review-artifact scaffolding; the real Home shows real owner data under truthful labels | Owner-directed; copy inventory reviewed at V2 |
| D3 (=R3) | Recent, Resurfaced, Noticed, Connections, and Next Step receive more distinct decorative personalities (abstract brand material per section) without fabricating member content | The candidate reuses near-identical dark landscape/starfield material; the binding baseline shows distinct per-section material | Owner-directed; new material must contain no people, records, counts, or member-like photography |
| D4 | Real owner data replaces fixture names/dates (Avery Morgan, Samira Patel, generic 2026-06-12 dates) | Fixtures are explicitly test-only in the accepted package | Inherent; two-owner fixture profiles remain for tests/screenshots |
| D5 | SVG Georgia/Arial stand-in typography is replaced by the licensed production pair: Newsreader (display serif) + Inter (UI) already loaded by `base.html` | The candidate's own component inventory declares Georgia/Arial as portability fallbacks; production typography is governed by the approved type system | Approved by the authority package itself; type scale must preserve the candidate's hierarchy |
| D6 | Candidate palette implemented as route-scoped tokens (`--oh-*`) in `owner-home.css`; shared `--ps-*`/`--pv-*` tokens and other routes unchanged | Exact-match owner decision for this surface without restyling released surfaces | Architecture decision; verify no leakage in V2 evidence |

## Manager decisions U1–U4 — resolved 2026-07-19

| ID | Binding decision | Evidence obligation |
|---|---|---|
| U1 | A server-owned `standalone_owner_shell`-style boolean exists only on the flag-on Owner Home render. `base.html` bypasses its forced-desktop tablet viewport code; suppresses the site sky, complete global header/profile strip, profile band, public footer, Ask Pete AI, public search data, global theme bootstrap/mobile chrome, and four public-chrome scripts; omits `portfolio-shell`/`platform-shell`, `slate-light`, and `ps-editorial-surface`; retains shared fonts/base styles, the skip link, and single base main. | Static/DOM tests plus representative flag-off `/app` and non-`/app` screenshots prove the conditional is inert everywhere else; 844/390/320 evidence proves native responsive reflow. |
| U2 | Ship the exact accepted `owner-home-alpine-atmosphere.png` for first release. No regeneration, recrop, recolor, substitute, or lossy derivative. | Hash the copied production asset against the preserved authority. Any later optimization is a separate parity-reviewed change. |
| U3 | Suppress global `mobile-tabbar` and `mobile-nav.js` for standalone Owner Home. Render exactly one page-scoped bottom nav: Home and Capture real; Journal, Slate, More disabled Coming later with no route/handler. | 390px/320px DOM and screenshots prove one nav, no duplicate focus stops, and no horizontal overflow. |
| U4 | Keep canonical `GET /app`; retain `owner_workspace.html` as exact flag-off fallback through frontend release and founding-alpha stabilization. | Flag-off regression tests and production verification; retirement only by later manager-approved cleanup. |

## Evidence obligations at V2/V3

Named comparison screenshots for every row of the parity map, at desktop
1440, mobile 390, mobile 320, and landscape 844, in loading/empty/populated/
failure/stale/restricted/recovery states, plus focus, forced-colors,
reduced-motion, and 200% zoom captures — each paired with its authority
export number. Pete and the designated session manager give final visual
acceptance against the real product; this register only defines the map.
