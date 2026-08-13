# PS-SHELL-001 — Shared global shell: the Editorial Top Bar

**Status:** Active writer lane, activated 2026-08-12 by PR 430 (main `9e91f58`).
Branch `work/2026-08-12-shell-editorial-top-bar-001`. Lane class
`shared_foundation`, delivery path Protected, exclusive domain `shared:shell`.
**Visual authority:** Direction 1, the Editorial Top Bar, approved by Pete on
2026-08-12 — structure and responsive behaviour. Direction 2 informs
medium-width overflow only. Direction 3 is rejected.
**Logo:** `static/images/peerslate-logo-header.png` is locked — not redrawn,
recoloured, cropped, reinterpreted, or substituted from any concept board.
**Implementation architecture:** [ARCHITECTURE.md](ARCHITECTURE.md).

> **Reconciled 2026-08-12.** The previous README predated every current
> decision. It specified a three-item nav, a two-tone ground "inverted between
> light and dark themes", per-room watermark silhouettes, a type-scale study,
> and a Fable/Sonnet/Opus routing line. All are superseded below. This package
> no longer owns palette selection or type scale; both belong to the cross-site
> Colour, Background, and Typography Audit.

## Scope

1. **One quiet, consistent global header** across public, signed-in member,
   owner, tablet, and mobile states. Page- and room-specific controls stay
   inside their rooms. No third persistent navigation tier.
2. **Responsive behaviour** on the existing breakpoint ladder: five inline
   destinations at wide desktop, a room-switcher pill at medium width, a
   purpose-built mobile structure below tablet — not a shrunken desktop nav.
3. **Authentication and account states**, preserving all five server-derived
   `auth_navigation_state` values, the accessible skip link, server-side
   authorization, and exact sign-in and deep-link return behaviour.
4. **Existing global search presentation and responsiveness.** No expansion of
   the search index, no content search, no change to authorization scope.
5. **A namespaced shell token family** — `--ps-shell-ground`, `-stage`,
   `-surface`, `-rail`, `-border`, `-text`, `-text-muted`, `-accent`, `-focus`
   and semantic status roles — defined as **aliases** of the production
   variables the shell already resolves, so tokenization is visually inert.
   Flat values, light-theme only, no alternate theme scaffolding.

## Destinations

Desktop navigation covers the five existing product destinations plus
authorization-aware search and an account control.

Mobile uses a purpose-built four-slot structure — Profile · Community ·
Interview · More — with Workshop, Opportunity Slate, Settings, Help and Sign
out under More.

**Add/Capture and notifications are not built.** `/app/capture` is owner-gated
behind a fail-closed allowlist (`owner_authorization.py`), so it is not the
reusable member contract the direction requires. No notification route, model
or service exists anywhere in the application. Both would be false affordances.
The layout reserves the Add slot so a future member capture contract is an
insertion rather than a re-layout.

**"Slate" is not a shell concern.** No Slate entry appears in the shell and no
new canonical meaning is assigned. Existing "My Slate" remains the
authenticated workspace ingress it is today.

## Owner decisions taken as stated assumptions

Pete granted full permission to complete the package on 2026-08-12 without
answering three open questions. Each is resolved below on the most truthful
reading, is cheap to reverse, and is flagged for his review.

**A1 — The first navigation item keeps its current label and destination.**
It stays "Pete's Slate" pointing at `portfolio_home_url`. The direction asks
for "Profile", but no per-member profile route is registered, and
`PS-PROFILE-CORE-INTEGRATION-001` explicitly forbids registering one in its
current lane. Labelling Pete's own portfolio "Profile" in a reusable
multi-user product would turn fixture content into shared product logic —
precisely what `app.py`'s `_interview_member_profile` guards against. The
label and href are a single data point so this changes in one place when
Profile registers a real member route.

**A2 — The anonymous navigation is unchanged.** All five destinations stay
visible to signed-out visitors, exactly as production renders them today; the
nav has no auth branch. This also matches the approved
`GLOBAL_SHELL_PUBLIC_MEMBER_OWNER` board. Hiding the sign-in-gated
destinations would be a behaviour change this package is not authorized to
make, and Pete's 2026-08-02 direction requires the two-mode audit before any
route gate moves.

**A3 — The account control carries an initial, never a photo.** No truthful
avatar source exists for the signed-in viewer; `author_avatar_url` is a
Community post-author field, not viewer identity. The control derives an
initial from `identity.display_name` with its existing "PeerSlate member"
fallback, and opens a menu containing only the controls that exist today — My
Slate and Sign out. Signed out, the existing Sign In button is unchanged.

## Owner round 2, 2026-08-13 — the mark is always revealed

Pete saw the rendered shell for the first time and gave one instruction above
all others: **"logo should always be revealed ... It should always be
revealed"**, naming 768–1024 signed in, where it was missing.

**This overrides the approved boards, and the divergence is recorded here
rather than argued.** `01_editorial_top_bar_LEADING_NOT_LOCKED.png` section C
and `02_room_switcher_MEDIUM_WIDTH_REFERENCE.png` section C both draw the
signed-in phone header with the room name **instead of** the mark, and
ARCHITECTURE.md §1 accepted that as authority. The pixel rule below already
settles the conflict: where a board and the owner's written direction disagree,
the owner's direction wins. So:

- `static/images/peerslate-logo-header.png` renders at **every width in every
  auth state**. It is not shrunk, cropped or re-proportioned to make room; the
  released desktop (2.2rem) and mobile (7.6rem × 1.65rem, `object-fit:
  contain`) boxes are unchanged.
- The room title now sits **beside** the mark behind a 1px divider, from
  34.01rem to 64rem, instead of replacing it.
- Below 34rem the **room title** stands down and the mark stays. The order of
  sacrifice is the owner's: room title, search label or nav text may go; the
  mark may not.

The same round asked for shell colour consistency — one semantic role, one
value, everywhere the shell renders. That is delivered in shell scope only.
**Interview Studio's sage, room grounds and page-owned colour are explicitly
out of scope** and belong to the cross-site Colour, Background and Typography
Audit; what this round found and did not fix is recorded as an audit input in
`IMPLEMENTATION.md` §14.

## Rules

- The **pixel rule** applies: accepted mockups' sampled pixels are the
  authority. Where the approved board and production truth disagree — the
  concept's green accent, its marketing nav, its "Get started" CTA, its
  wordmark — production and the owner's written direction win, and the
  divergence is recorded.
- **Use existing production colours.** Do not invent a competing global
  palette. Room colour stays subordinate to the shell foundation.
- **Colour carries no layout meaning.** No breakpoint, spacing or component
  structure keys off a palette value, so the later audit can change values
  without rebuilding layout or behaviour.
- **No new dark rules**, and no removal of existing dormant ones. The token
  layer must not become a theming mechanism.
- Do not use CSS `zoom`, transforms, raster scaling, or portrait concept-board
  dimensions to make the shell fit a viewport.
- One writer, one branch. Navigation gains no destination that lacks a real
  page.
- Accessibility corrections inside shell scope are authorized and must be
  recorded individually with measured before and after values. They are the
  only permitted visual delta at tokenization.
- This package does not by itself approve every route's tablet or phone
  composition, and does not close the cross-site responsive audit.

## Delivery

**Routing (Pete, 2026-08-12):** Opus max architects → Opus extra-high
implements → fresh Opus max reviews. Supersedes the prior Fable/Sonnet/Opus
line.

**Sequence:** activation → implementation worktree → shell structure and
responsive behaviour → authentication and account states → search presentation
→ pre-tokenization screenshot baseline → tokenize by aliasing → post-tokenization
diff → cross-route verification → complete-diff self-review → independent
review → merge grant → release grant.

**Exclusions:** homepage body, copy, imagery, marketing sections, SEO or
walkthrough; Profile, Interview Studio, Opportunity Slate, Community,
Workshop, résumé and My Story content; the logo; owner-specific product logic;
automatic saving, routing, publication or audience change; search
authorization; schema or production data; dark-theme revival; `app.py`,
migrations, provider configuration and page templates.

## Deferred to the Colour, Background and Typography Audit

Palette selection including whether the shell's accent stays blue; type scale
and the three loaded font families; the unadopted parallel
`design-system/tokens.css`; the misleadingly named `--color-gold-bright`, which
resolves blue under the live theme; the still-gold `--ps-focus-ring`; the inert
room-accent system, where six rooms all map to one colour; and the full
cross-site computed-style and hardcoded-colour inventory.
