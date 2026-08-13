# PS-SHELL-001 — Editorial Top Bar: implementation architecture

Architect: Claude Opus 5 (max effort), 2026-08-12. Base `9e91f58`.
Read [README.md](README.md) first for scope, rules and the three stated
assumptions A1–A3.

---

## 1. What the approved visuals do and do not authorize

Direction 1 (`01_editorial_top_bar_LEADING_NOT_LOCKED.png`) is authority for
**geometry, composition and responsive behaviour only**.

| Concept element | Status | Why |
|---|---|---|
| Deep-green accent | **Not authority** | Production theme is `light_modern_blue`; the owner's addendum defers blue usage to the Colour audit and forbids a competing palette. |
| Public nav: Product · How it works · Pete's Slate · Try Interview Studio | **Not authority** | The direction excludes final public marketing navigation and the "How it works" story. |
| "Get started" CTA | **Not authority** | Homepage calls to action are excluded. |
| Letterspaced PEERSLATE wordmark | **Not authority** | The production logo file is locked. |
| One quiet row, white ground, thin bottom rule | **Authority** | |
| Underline active-state indicator | **Authority** | |
| Room rails render *below* the shell, never inside it | **Authority** | Room controls stay page-owned. |
| Signed-in mobile header shows room title, not logo | ~~**Authority**~~ — **SUPERSEDED 2026-08-13** | The owner, having seen it rendered: "logo should always be revealed ... It should always be revealed." The mark renders at every width in every auth state; the room title sits beside it and stands down below 34rem. README's pixel rule governs — the owner's written direction beats the board. See README "Owner round 2" and IMPLEMENTATION.md §14.1. |
| Mobile bottom bar structure | **Authority**, contents adjusted — see §3 | |

Direction 2 supplies **only** the medium-width mechanism: the inline
destinations collapse into a single room-switcher pill showing the current room
with a chevron, opening a labelled list. Its More sheet (Workshop, Opportunity
Slate, Settings, Help, Sign out) matches the required mobile spec and may be
used.

`GLOBAL_SHELL_PUBLIC_MEMBER_OWNER.png` supplies the three-state comparison. Its
owner variant shows a second row — "Your Profile / Add something / Manage /
View as public". **That row is Profile-owned page furniture, not shell.** The
same board's footer forbids a third persistent navigation tier, and room
controls stay in rooms. Therefore:

> **The shell's owner state is identical to the member state.** That row
> belongs to the Profile package. This package does not build it.

---

## 2. Preserve exactly — these are contracts

- The skip link `<a class="skip-link" href="#main-content">`.
- All five server-derived `auth_navigation_state` values: `authenticated`,
  `workspace_waking`, `account_issue`, `signed_out`, `auth_unavailable`. Every
  control renders server-side; `auth-state.js` only toggles the `hidden`
  attribute after a bounded same-origin principal check and never builds HTML
  or reads browser auth storage. **Do not move any of this to the client.**
- `public-navigation.css` loading **after** every page stylesheet. This is the
  mechanism that holds one geometry when a legacy page package still ships
  route-specific header rules.
- The touch-tablet viewport script forcing real tablets ≥744px to render at
  1280px, with `/resume`, `/slate-board` and `/interview-studio` exempt.
  **Consequence:** a real iPad gets the desktop layout, so the 1024/768 checks
  exercise a *different* code path than a resized desktop browser. Test and
  report both separately.
- `data-theme="modern-blue"` on `<body>` and the `PEERSLATE_DARK_THEME_ENABLED`
  gate keeping dark dormant. No new dark rules; no removal of existing ones.
- Exact sign-in return and deep-link behaviour.
- The existing `mobile-tabbar` contract, including `body.has-mobile-tabbar`
  bottom padding — see §5.

---

## 3. Composition

**Destinations (unchanged from production):** Pete's Slate → `portfolio_home_url`,
Community → `the_slate`, Interview Studio → `interview_studio_url`, Workshop →
`workshop_url` (flag-gated on `workshop_nav_enabled`), Opportunity Slate →
`opportunity_slate_url`. Rendered unconditionally to everyone, per assumption
A2. Active state via `aria-current="page"`, indicated by an underline.

**Not built:** notification bell (no route, model or service exists) and a
global Add/Capture control (`/app/capture` is owner-gated behind a fail-closed
allowlist, not a reusable member contract). Reserve the Add slot between search
and the account control so a future member contract is an insertion, not a
re-layout.

**Account control (A3):** an initial derived from `identity.display_name`,
never a photo. Opens a menu containing only My Slate and Sign out — the
controls that exist today. Signed out, the existing Sign In button is
unchanged. The menu must be keyboard operable, labelled, dismiss on Escape and
outside click, and return focus to its trigger.

---

## 4. Responsive ladder

Keep the existing breakpoints in `public-navigation.css`: `73.75rem/64.01rem`,
`64rem`, `34rem`, `22rem`. Do not introduce a parallel set.

| Width | Structure |
|---|---|
| ≥ 73.75rem | Logo · five inline destinations · search · account. One row. |
| 64.01–73.75rem | **Room-switcher pill** replaces the inline items. Search is currently `display:none` in this band — restore it, since the pill frees the space that forced its removal. |
| ≤ 64rem | Mobile. ~~Logo (signed out) or room title (signed in)~~ **Superseded 2026-08-13: logo always, plus the room title beside it from 34.01rem up** · search · account. Global bottom bar. |
| ≤ 34rem | Compact action row; keep the existing `:has()`-scoped sizing. |
| ≤ 22rem | Icon-only controls; keep existing behaviour. |

---

## 5. The bottom-bar collision — resolve before building

`base.html` already ships `<nav class="mobile-tabbar" id="mobile-tabbar">`. It
is **not** global navigation: `mobile-nav.js` clones the current page's
`[data-mobile-tabsource]` links into it, so it mirrors page-section tabs.

A global bottom bar would be a *second* fixed bottom bar. Two is unacceptable,
and repurposing `.mobile-tabbar` would silently change page-owned behaviour on
every route that populates it.

**Required resolution for this package:** the global bar renders **only on
routes with no section tab source**. Where a page supplies section tabs, the
existing tabbar keeps its current behaviour untouched. Record the alternative —
moving section tabs inside each room's content so the global bar is universal —
as a dependency for the destination-stabilisation phase; it edits room-owned
surfaces and is out of scope here.

Whichever bar renders must participate in the same `body.has-mobile-tabbar`
padding contract, or content will sit underneath it.

---

## 6. Unify the forked shell

The single largest structural defect: the shell is **duplicated** between owner
and public paths.

| Concern | Owner path (`/app*`) | Everything else |
|---|---|---|
| Search JS | `site-search.js` | `public-site-search.js` |
| Mobile nav JS | `mobile-nav.js` | `public-mobile-nav.js` |
| Nav CSS | `public-navigation.css` **not loaded** | loaded |
| Search index | owner branch of `#nav-search-data` | public branch |

"One quiet, consistent global header" cannot be true while two implementations
exist. Converge on one component set with server-side state branching, and
delete a duplicate only after the survivor passes both paths' tests.

**Caution:** `/app` is the deferred legacy owner workspace and its flag-off
render is byte-locked by `tests/test_owner_home.py`. If convergence would break
that lock, leave `/app` on its current path and record the divergence as
deferred. Do not modify that test.

---

## 7. Token layer

### 7.1 Alias, never duplicate

Production already carries an unprefixed semantic vocabulary that
`public-navigation.css` consumes today. Those variables are **contextual** —
redefined at `:root`, `body[data-theme="modern-blue"]`, `body.slate-light`,
`.peerslate-home-page` and dormant dark variants. Live resolution for a normal
page is `:root` → `body[data-theme="modern-blue"]` → `body.slate-light`.

Define the shell family as aliases:

```css
:root {
  --ps-shell-ground:      var(--bg);
  --ps-shell-stage:       var(--bg-elevated);
  --ps-shell-surface:     var(--surface);
  --ps-shell-rail:        var(--surface-soft);
  --ps-shell-border:      var(--border);
  --ps-shell-text:        var(--text);
  --ps-shell-text-muted:  var(--text-muted);
  --ps-shell-accent:      var(--accent);
  --ps-shell-accent-soft: var(--accent-soft);
}
```

Hardcoding literals would **break** every context that resolves differently and
silently repaint pages. Aliasing guarantees the computed value is identical to
today's — which is what makes the §8 pixel check meaningful — and gives the
Colour audit two levers: change `--accent` globally, or override
`--ps-shell-accent` for the shell alone.

### 7.2 Live values, recorded not hardcoded

Under `body.slate-light`: ground `#fdfdfe`, stage `#ffffff`, surface `#ffffff`,
rail `#f4f8fd`, border `#d9e2ec`, text `#061a3a`, muted `#49617a`, accent
`#0b63e5`, accent-soft `rgb(11 99 229 / 8%)`, serif `Newsreader`. Recorded so
the audit sees what it is changing. **Reference the variables, not these
literals.**

### 7.3 Focus is the one value defined rather than aliased

There is no clean production focus token:

- `a:focus-visible, button:focus-visible { outline: 3px solid var(--color-gold-bright) }`
  — and `--color-gold-bright` is `#ffd36a` at `:root` but **`#4a83e8` under
  `body[data-theme="modern-blue"]`**. The live ring is blue, from a variable
  named gold.
- `--ps-focus-ring` is a composite box-shadow still hardcoded gold.

Define `--ps-shell-focus` with an honest name. **Measure `#4a83e8` against
`#fdfdfe` for WCAG 2.2 SC 1.4.11 (3:1 non-text contrast) before choosing a
value.** If it passes, alias it and change nothing. If it fails, this is the
authorized accessibility correction — record measured before/after ratios as
the sole intentional visual delta.

### 7.4 Room colour must become subordinate

`style.css` styles `body[data-room] .platform-nav__links a[aria-current="page"]`
and its `::after` underline — room colour currently reaches into the shell's
active-state indicator. The shell's active state should resolve from
`--ps-shell-accent`, with any room tint applied as an explicitly scoped,
documented exception rather than an override winning by cascade position.

Observed for the audit: the room system is effectively inert. `bronze`, `teal`,
`plum`, `amber`, `pine` and `ultraviolet` all set
`--ps-page-accent: var(--ps-primary)` — six rooms, one colour.

### 7.5 Rules

Flat values, light only. No `@media (prefers-color-scheme)`, no second value
set, no theme-switching scaffolding — a variable layer is exactly how a paused
dark theme returns by accident. Shell-owned CSS only; page-owned rules keep
their current values. Do not adopt `design-system/tokens.css`: it is a parallel
`--ps-*` system built so it "cannot accidentally restyle the existing website",
and its values differ from live (`#f7faff` vs `#fdfdfe`; `#4ea3ff` vs
`#0b63e5`). Record the divergence; do not resolve it here.

---

## 8. Verification

**Tokenization must be a discrete step.** Pixel-identity is measured against
the completed shell immediately before tokenization, not against current
production — the new shell legitimately changes navigation geometry.

1. Build the shell with production colours referenced as they are today.
2. Capture the full screenshot set. This is the baseline.
3. Tokenize as a mechanical alias substitution.
4. Recapture and diff.
5. Any non-zero diff is a defect or the §7.3 focus correction. Nothing else.

**States:** signed-out public desktop · signed-in member desktop · owner
desktop (must equal member) · medium width · tablet · signed-out mobile ·
signed-in mobile · account menu open · search open/results/empty/unavailable ·
session expired and sign-in recovery · keyboard and 200% text. Notification and
Add states are omitted by §3 — record the omission and its evidence rather than
leaving rows blank.

**Viewports:** 1440×900 · 1280 · 1024 · 768 · 390×844 · 320 · 200% zoom, with
real-tablet behaviour reported separately from resized-desktop.

**Checks:** active states · no horizontal overflow at any width · no duplicate
navigation · room controls still page-owned · search authorization unchanged ·
exact sign-in and deep-link return · refresh, second tab, session expiry,
sign-out · keyboard order, visible focus, labels, touch targets, screen-reader
structure · no console errors · existing page workflows intact · Profile's
focused suites unaffected.

**Search:** global search is a **client-side destination index**
(`#nav-search-data`), not content search, with separate owner and public
branches filtered in the browser. Restyle presentation and responsiveness only.
Do not expand the index, add content search, or change what either branch
exposes. Recorded for later: the public branch carries Pete-specific fixture
entries, a fixture concern for the destination-stabilisation phase.
