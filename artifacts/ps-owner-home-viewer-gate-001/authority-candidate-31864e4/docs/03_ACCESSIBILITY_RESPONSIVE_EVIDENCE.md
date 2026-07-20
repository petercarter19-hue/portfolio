# Accessibility and responsive evidence

Target for any authorized implementation: WCAG 2.2 AA.

Static mockups can demonstrate intended layout, labels, visible focus, contrast treatment, structured order, state copy, and absence of fabricated data. They cannot prove runtime semantics, DOM exclusion, request suppression, server authorization, focus movement, live-region behavior, NVDA output, orientation persistence, or media-query execution. Those remain implementation acceptance criteria.

| Evidence | Export | What the visual proves | Still requires implementation verification |
|---|---|---|---|
| Desktop current | 01 | One dominant Capture; private context; polished dormant capabilities | Semantic landmarks, server-derived actions, disabled DOM behavior |
| Desktop maximum fixture | 02 | Exact nine-object maximum, 3 reviews, bounded remainder, generic fixture labels | Selector/query limits, authorization, deduplication |
| 390 px current/future | 03–04 | Standalone full-scroll sequence, complete bottom nav, no phone crop | Touch behavior, sticky obstruction, orientation and keyboard handling |
| 320 px current/future | 05–06 | Exact-width reflow, no horizontal canvas, complete **Coming later** labels | Browser 320 CSS-pixel test, target-size measurement, 400% reflow |
| 200% structured reading | 07 | 512 CSS-pixel equivalent at 200%, enlarged readable text, one visual column, preserved order | Actual browser zoom, DOM order, focus order, text-spacing overrides |
| Long content | 08 | Long owner name, wrapped review and Moment titles, explicit missing-media fallback, and SVG bidirectional direction treatment | API bounds, browser `dir` behavior, disclosure behavior, unbroken-string CSS |
| Visible focus | 09 | Marigold focus ring plus dark separation edge on Capture | Keyboard reachability, focus contrast calculation, unclipped runtime focus |
| High contrast | 10 | Meaning survives with black/white, borders, and text status | Windows forced-colors token mapping and NVDA/Chromium test |
| Reduced motion | 11 | No motion is required for state, order, or loading meaning | `prefers-reduced-motion`, immediate revocation, runtime animation removal |
| Loading | 12 | Stable heading and component silhouette; no fake records or counts | One polite announcement; skeletons `aria-hidden`; no cached private fallback |
| Empty | 13 | Honest empty Review/Recent and dominant Capture | Announced empty state and semantic section labeling |
| Partial failure | 14 | One failed category, successful independent categories retained | Same bounded retry request and focus retention |
| Complete failure | 15 | Clear failure, Retry, safe return, independently safe Capture | Error live region, focus placement, no raw IDs, session handling |
| Stale | 16 | Explicit Stale, protected action stopped, Refresh shown | Concurrency enforcement and no silent overwrite |
| Restricted | 17 | Neutral, non-enumerating unavailable treatment and safe return | Server/payload/DOM removal and authorization response |
| Recovery | 18 | Success and repeat-failure treatments; visible intended focus | One completion announcement and predictable focus movement |
| Access/lifecycle | 22 | Distinct viewer-empty/unpublished wording plus revoked, deleted, session-expired, timeout, and fail-closed treatments without owner controls | Sensitive DOM/cache/media clearing, authorization, live regions, focus movement, safe URL behavior |
| Landscape orientation | 23 | Standalone 844 px full-scroll landscape-width document with preserved data order and bottom navigation | Real device orientation change, state/focus preservation, system keyboard, and viewport-height obstruction |

## Structured order

The responsive reading order is:

1. Brand/header
2. Owner Home heading and private context
3. Capture
4. My Slate and audience shell
5. Needs Review
6. Recent Moment
7. Resurfaced Moment
8. What PeerSlate noticed
9. Connections
10. Next Useful Step
11. Status/footer
12. Bottom navigation on mobile

## Runtime acceptance checklist

- One descriptive `h1`; logical headings and useful sections/lists.
- Capture is a real protected link or button with an unambiguous name.
- Capability screen-reader wording: `[Feature] — coming later. Not yet available.`
- Disabled capabilities are non-requesting, excluded from forms, non-focusable as controls, and remain explained in reading order.
- Logical keyboard order, no trap, visible focus, Skip to main/review, and normal Back/Forward/Refresh/Escape behavior.
- Loading, completion, failure, stale, restricted, revoked, and recovery announcements are concise and non-duplicative.
- Public and permissioned payloads/DOM contain no owner controls; CSS hiding is insufficient.
- 200% zoom, 320 CSS px, 400% reflow where applicable, text-spacing overrides, Windows high contrast, reduced motion, touch, portrait/landscape, long and bidirectional content.
- NVDA on supported Chromium plus automated semantic scanning.
- No private text, grant secret, revealing title, analytics label, clipboard default, or raw internal identifier leak.

## Acceptance boundary

Static evidence disposition: **Conditional**. Runtime accessibility is **not yet verified** because no implementation was authorized or performed.
