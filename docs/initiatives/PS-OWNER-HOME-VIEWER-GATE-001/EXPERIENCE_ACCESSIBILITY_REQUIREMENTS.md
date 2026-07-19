# PS-OWNER-HOME-VIEWER-GATE-001 Experience and Accessibility Requirements

## Boundary

These requirements define behavior and acceptance criteria, not final visual composition. The production-intent Home and viewer designs still require ChatGPT Work and Pete acceptance under the Owner Visual Integrity Standard before implementation is visually complete.

Target: WCAG 2.2 AA across keyboard, screen reader, touch, zoom, reflow, high contrast/forced colors, and reduced motion.

## Understandable context

Every page must answer, in accessible text near the page heading:

- **Whose space is this?** Use an authorized display label, not an internal key.
- **What context am I in?** Owner Home, owner preview, selected-person view, connection view, member view, or public view.
- **What can I do here?** Capabilities are derived by the server and expressed as concrete actions.
- **What is not happening?** Private/draft/unpublished labels must make clear that viewing or previewing did not publish, share, connect, or save anything.

Owner preview requires a persistent, non-color-only banner naming the preview mode and stating that the owner is previewing the real authorized projection. If the selected mode has no real eligible viewer/grant/relationship, the page must say that the mode is unavailable and why; it must not simulate a person.

Public and permissioned viewers must not see owner controls. Hiding those controls with CSS is insufficient; they must be absent from the server payload/DOM.

## Semantic structure

- One descriptive `h1` per page. Sections use a logical heading hierarchy with no skipped levels caused by styling.
- The Capture action is a real link or button according to behavior, with an unambiguous accessible name. It is not a clickable `div`.
- Home categories are landmarks/sections only when their labels help navigation; avoid landmark noise for empty wrappers.
- Review items and projected sections use lists when order/grouping matters. Visual placement does not replace semantic reading order.
- Dates/times use semantic markup and include understandable absolute text; relative text such as "2 days ago" has an accessible absolute equivalent.
- Statuses such as Private, Draft, Published, Restricted, Revoked, Deleted, and Stale use text plus any visual treatment. Color or icon alone is prohibited.
- Icons are decorative when adjacent text already names the action; otherwise they have an accessible name. No file-name or emoji-only labels.
- Member-authored headings and summaries preserve meaning but cannot inject heading levels, landmarks, scripts, or unsafe markup.

## Keyboard behavior

- All controls and destinations are reachable and operable with keyboard alone in a logical order matching semantic reading order.
- No keyboard trap. Standard browser Back, forward, refresh, and escape expectations remain intact.
- Tab order does not follow a decorative desktop layout when that conflicts with document meaning.
- Enter activates links; Enter/Space activates buttons; custom disclosure/listbox behavior follows the applicable ARIA Authoring Practices pattern.
- When a mode selector is eventually designed, it must use a native control or a complete accessible pattern. Changing a selection must not navigate or fetch without clear activation unless that behavior is announced in advance.
- Retry, Refresh, sign-in, return-to-Home, and safe-exit actions are keyboard reachable in every failure/revoked state.
- No pointer-only hover controls. Any contextual actions have keyboard and touch equivalents and remain discoverable on focus.

## Focus management and visible focus

- Every interactive element has a visible focus indicator meeting WCAG 2.2 contrast/area expectations across light, high-contrast, and forced-colors modes.
- Initial page load leaves focus in the normal document flow; it is not moved automatically to promotional content.
- Client-side category refresh keeps focus on the invoking Retry/Refresh control unless that control disappears, then moves focus to the updated section heading with `tabindex="-1"`.
- A full route change moves focus predictably to the new page heading or allows native navigation to do so; the document title also changes.
- When access is revoked while content is open, remove/replace sensitive content before moving focus to the access-changed heading. Do not leave focus on a detached private element.
- Validation or state-change errors receive programmatic association and a concise summary; focus is not repeatedly stolen by background polling.
- Skip navigation reaches the main content and, where useful, the finite review section. A large global navigation redesign is out of scope.

## Screen-reader announcements

- Initial loading uses one polite status announcement. Skeletons are `aria-hidden` and contain no fake text/counts.
- A completed load announces a short result such as "Home updated" only when initiated dynamically; it does not read every card.
- Failure, stale, revoked, and restricted changes are announced with the appropriate polite or assertive live region based on urgency.
- Repeated retries do not produce duplicate announcement storms.
- Category counts reflect the bounded objects actually returned. Do not announce hidden or unauthorized totals.
- Preview mode and viewer context occur in the title/heading/context description, not only in a badge.
- Empty sections use concise real text. They do not expose internal error codes or imply that private content exists for another viewer.

## Desktop behavior

- The opening viewport preserves one dominant product object/action: Capture on Owner Home, or the viewer's projected Slate in viewer mode.
- Supporting categories may continue vertically. They are not compressed into a dashboard grid merely to fit above the fold.
- At common desktop widths, text lines remain readable and long summaries do not push controls off-screen.
- If a multi-column presentation is later approved, DOM/reading order remains meaningful when columns collapse, and zoom does not cause cross-column focus jumps.
- The page remains usable with browser sidebars, increased default fonts, and content at least 200% zoom.

## Mobile and reflow behavior

- At 320 CSS pixels wide and at 400% zoom where the WCAG reflow criterion applies, content uses readable document flow with no two-dimensional scrolling except an intrinsically necessary object separately justified.
- No desktop visualization is miniaturized until labels/actions are unreadable. Sections stack in semantic order.
- Touch targets meet WCAG 2.2 target-size requirements or documented exceptions and have adequate separation.
- Sticky/fixed UI must not obscure the page heading, focused control, status message, or system keyboard content.
- Controls do not depend on hover. Context menus/actions have persistent touch entry points.
- Orientation is not locked. Portrait and landscape preserve data and focus when layout changes.
- Long member text wraps without horizontal overflow; URLs and unbroken strings use safe wrapping without truncating the only meaningful label.

## 200% zoom, text spacing, and long content

- At 200% browser zoom, all content/actions remain visible without overlap or clipping, and focus indicators are not cut off.
- User text-spacing overrides do not hide or overlap controls.
- Titles, names, and summaries are bounded by the API for performance but may be longer than fixture examples. The UI supports the maximum without fixed-height clipping.
- Truncation, if approved, exposes the complete authorized text through a keyboard/screen-reader/touch-operable disclosure. A tooltip alone is insufficient.
- Missing title/media/optional metadata has a semantic fallback. Broken media does not remove the text alternative or primary action.
- Translated and bidirectional text is allowed in member content. Layout cannot assume English word length or left-to-right authored text, even if application chrome remains English initially.

## Motion and reduced motion

- Motion is never required to understand loading, mode, access, or ordering.
- Prefer opacity/transform for optional transitions; avoid parallax, automatic carousels, celebratory motion, or reordering animation.
- `prefers-reduced-motion: reduce` removes non-essential animation and animated scrolling while preserving immediate state changes and focus placement.
- Loading indicators remain understandable when animation is disabled.
- Access revocation removes content immediately; it is not delayed by an exit animation.

## State requirements

| State | Accessible experience requirement |
|---|---|
| Loading | Stable page heading and section labels; one status announcement; inert/hidden skeletons; no fake records or counts |
| Empty Home | Explain what is empty and the real next available action; Capture remains obvious when available |
| Empty published projection | Identify the subject/context and say there is no published content in this view; do not imply private content exists |
| Private/unpublished owner item | Text label communicates status and that preview/management did not publish |
| Restricted/not found | Neutral unavailable heading and safe navigation; do not reveal whether the subject or private record exists |
| Revoked/access changed | Sensitive DOM and client state cleared, explicit access-changed message, focus moves to heading, no stale fallback, safe exit/retry |
| Deleted | Approved tombstone only when the lifecycle calls for it; no reconstructed body; current actions disabled/removed |
| Stale concurrency | Explain that the item changed, preserve no uncommitted mutation silently, and provide Refresh/return action |
| Partial Home failure | Failed category names itself as unavailable and offers Retry; successful independent categories remain understandable |
| Complete failure | Clear heading, concise explanation, Retry, and safe navigation/sign-in; no raw stack/error identifier |
| Slow response | After an agreed threshold, update status text without starting duplicate requests; user can still navigate safely |
| Retry succeeds | Update section, announce completion once, and place/retain focus predictably |
| Retry fails | Preserve user context and repeatable control; do not append duplicate errors |

## Security and privacy in the experience

- Do not put private text or opaque grant secrets in URL query strings, page titles, analytics labels, HTML comments, data attributes unrelated to rendering, clipboard defaults, or error messages.
- Browser history and recently closed tabs must not gain a more revealing title than necessary for permissioned views.
- External links from authorized content use safe referrer behavior and visibly identify destination/new-window behavior when applicable.
- Screenshots used for review use approved generic fixture profiles unless Pete and Danielle explicitly consent to a named founding-alpha validation capture. Private production content is not placed in repository artifacts.
- A public route viewed while signed in remains public-mode content; the experience must not quietly blend private controls/data into a shareable page.

## Owner Settings experience intersections

Future audience/default changes must:

- name the affected audience in plain language;
- distinguish default for new content from existing content;
- preview affected records/viewers before any bulk change;
- require explicit confirmation for visibility broadening, withdrawal, or deletion;
- provide a recoverable validation error and row-version conflict flow;
- never use prechecked publication/sharing/connection consent.

The current informational Settings screen must not be visually represented as though these controls already work.

## Acceptance matrix

Every implementing frontend package must test at minimum:

- keyboard-only use of all page states and actions;
- NVDA with a supported Chromium browser on Windows, plus an additional automated semantic scan;
- 200% zoom and 320 CSS-pixel reflow;
- Windows high contrast/forced colors;
- reduced motion;
- touch/mobile viewport and orientation change;
- long names/titles/summaries, missing optional data, deleted reference, and translated/bidirectional sample content;
- each viewer mode's context wording and absence of owner controls;
- loading, empty, partial failure, total failure, stale, restricted, revoked, and successful retry;
- screenshot comparison at named desktop and mobile sizes against the owner-approved visual authority.

Automated accessibility checks are necessary but not sufficient. Pete and Danielle founding-alpha validation must include understandable context, trust/privacy comprehension, and real keyboard/mobile tasks, not only visual preference.
