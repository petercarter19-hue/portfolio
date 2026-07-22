# PS-COMMUNITY-TABS-001 — Authority integration map

**Status:** Implementation authority for the Community correction lane.

**Owner-superseding decision (2026-07-21):** Community has exactly two
first-class views: **Feed** and **The Break**. The pre-existing package and
shared-governance references to Saved are stale for this lane and are not
implementation authority. `/the-slate/saved` remains a compatibility redirect
to `/the-slate`; it must never render a third panel, tab, keyboard stop, or
Saved destination. This file records the override locally without changing
reserved shared governance pointers.

## Authority set

| Reference | Role | Binding use |
| --- | --- | --- |
| `visual-authority/owner-approved-dark-break.png` | Primary, owner-approved dark full-page authority | Break hierarchy, material depth, dark palette, imagery, compact/mobile order. |
| `visual-authority/owner-approved-light-break-2026-07-21.png` | Required light counterpart | The same component structure as the current dark authority in warm-ivory and pale-sage materials; not a separate layout. The older unversioned light concept is superseded and disregarded. |
| `static/images/Mockups/Break Feed.png` | Atmosphere and content reference only | Retain restorative editorial tone and content grouping; do not inherit its obsolete product shell, logo, nav, routes, or unsupported controls. |
| `artifacts/ps-community-tabs-001/desktop-1440-light-feed.png` | Current-site integration reference | Preserve the actual signed-in header, profile row, centered Feed grid/gutter, Feed rail, footer, and seam into Break. |
| `static/images/community/break-*.png` | Production imagery | Use the supplied chair/plant, transformation, and bookstore photography in their named roles; no image is a UI screenshot or member record. |

## Element decisions

| Element | Decision | Rationale and controlling requirement |
| --- | --- | --- |
| Signed-in PeerSlate shell | Adapt | Retain the real header, My Story / Work / Slate Board / Resume row, and footer from the current shell. The authority's obsolete logo/navigation is excluded. |
| Global navigation | Exclude | The mockup's old global navigation and `/the-slate/*` destinations do not define current product navigation. The existing Community link remains truthful. |
| Community switcher | Adopt | Use exactly two accessible tabs, Feed and The Break, with roving tabindex, ARIA tab/panel wiring, progressive-enhancement URLs, history, back/forward, and no reload on normal activation. |
| Saved Community view | Exclude | Owner supersession: remove the Saved destination, view state, panel, tab, keyboard stop, indexing, route claim, and saved-fixture surface. `/the-slate/saved` only redirects to Feed for compatibility. The established per-post `Save` action remains a local Feed action; it never exposes or navigates to a Saved Community view. |
| Feed panel | Adapt | Preserve current Feed data/interaction truth and its centered main-column/right-rail grid. The switcher becomes a two-tab control; the retained per-post `Save` action is local to the rendered Feed and does not claim persistence or a destination. |
| Break heading / notice | Adopt | Retain `The Break`, restorative subtitle, and visible sample-community truth notice. Align these to the Feed main column rather than make a landing-page hero. |
| Break content hierarchy | Adopt | Keep the authority's exact restorative sequence: hero; transformation; paired challenge/poll; discovery; Mood; quote; Pick-Me-Up; share; return. It is one integrated primary-column flow. |
| Break imagery | Adopt | Use supplied production chair/plant for hero, transformation for before/after, bookstore for discovery. Apply documented `object-position` crop rules per breakpoint. |
| Break copy and data | Adapt | Keep illustrative, sample-community labels and avoid invented member identity, persistence, APIs, counts, or availability. Existing static copy is fixture-only. |
| Break controls | Adapt | `Back to the Feed` switches tabs. `Create a post` switches to Feed and focuses the real composer. Unsupported saves, details, hearts, and board actions are removed or truthfully disabled without false destinations. |
| Break state | Adapt | Mood selection remains local visual state with accessible pressed semantics; challenge/poll are illustrative and non-persistent. Do not call Break data APIs or enable either existing feature flag. |
| Persistent Break right rail | Exclude | The older integrated draft incorrectly stranded Mood, quote, Pick-Me-Up, and share in a desktop rail. The approved dark authority places them after discovery in the same restorative sequence, so they are never pinned as a second module column. |
| Desktop layout | Adapt | Preserve the measured Feed integration shell: 1260px outer width, 860px primary track, 320px companion track, 36px gap, and matching title/tab alignment. Inside that shell, Break content occupies the integrated 860px primary flow; Break is not a full-width landing page or a persistent two-column module dashboard. |
| Mobile layout | Adopt | Match authority's compact shell, full-width theme materials, two-tab rhythm, card order, touch targets, and non-overlapping navigation. Reflow content rather than shrink desktop. |
| Theme | Adopt | The same system supplies genuine end-to-end dark and warm ivory/pale-sage light. No white content sheet remains below dark chrome. Navy, sage/moss, antique gold, and WCAG-aware contrast replace retired iris/purple semantics. |
| Motion / focus / zoom | Adopt | Honour reduced motion, keyboard focus/arrow navigation, direct load, history, and 200% reflow. No animation is required for the switch to be understandable. |
| Footer | Adapt | Preserve the authentic current footer while carrying the authority's quiet closing rhythm. |
| Homepage projection | Exclude / record | No homepage Community projection is currently identified in the active materials. This package changes no homepage surface; downstream parity is not claimed. |

## Truth boundary

The community rows, names, imagery, counts, quote, challenge, poll, Mood, and
Pick-Me-Up are sample fixtures. They are neither real members nor a production
social, Saved-view, board, poll, or discovery system. The established per-post
`Save` control is explicitly local to the rendered Feed; it does not imply
persistence or a destination. The route and tab mechanics are live client
behavior; content persistence and the excluded actions are not.

## Accepted deviations from visual authorities

1. The production page keeps the real PeerSlate shell and current Feed width,
   rather than reproducing the mockup's obsolete global navigation.
2. Unsupported mockup saves, discovery links, and board controls are removed or
   disabled rather than acting as false affordances.
3. A two-tab switcher replaces the superseded three-tab source materials.
