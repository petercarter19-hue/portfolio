# PS-SHELL-001 — Editorial Top Bar: implementation record

Writer: Claude Opus 5, 2026-08-12. Branch
`work/2026-08-12-shell-editorial-top-bar-001`, base `9e91f58`.
Read [README.md](README.md) for scope and assumptions A1–A3, and
[ARCHITECTURE.md](ARCHITECTURE.md) for the authority this implements.

This record covers stages 1–4 of the package sequence: shell structure and
responsive behaviour, authentication and account states, search presentation,
and **tokenization (architecture section 7), which is now done and measured
inert** — see §11.

---

## 1. What changed

| File | Why |
|---|---|
| `templates/base.html` | Room label / account name / initial derivation; phone room title; medium-width room switcher; account control replacing the two authenticated pills; More-sheet account group; global bottom-bar source list; reserved Add slot marker. Every addition is inside a `not is_owner_app_path` guard placed so the `/app` render gains zero bytes. |
| `static/css/public-navigation.css` | The Editorial Top Bar itself: ground, rule, brand, destinations, active state, room switcher, account control, search, mobile structure, bottom-bar rules. |
| `static/js/public-mobile-nav.js` | Disclosure behaviour for the room switcher and account menu; the bottom bar now falls back to the global source list where a page supplies no section tabs; the More slot reuses the one destination sheet. |
| `tests/test_navigation.py` | Room switcher parity with the inline row, phone room title, global bar source, More sheet, no-notification/no-Add, and a pin on the deferred `/app` fork. |
| `tests/test_auth.py` | New `ShellAccountControlTests`: all five states server-rendered, initial-not-photo, menu contents, the sign-out form's own state attribute, no client-side auth, unchanged sign-in return. |
| `tests/test_search_visibility.py` | New `ShellSearchScopeTests`: index unchanged, no new records, branches unmixed, `/app/settings` still uncrawlable, field reachable at every width, search JS still index-only. |
| `artifacts/2026-08-12-shell-editorial-top-bar/**` | The 150-frame shell baseline and its digests, the responsive probe, the review-fix measurements, the tokenization diff report, and four reproducible scripts (`capture_shell_baseline.py`, `verify_shell_responsive.py`, `verify_shell_interaction.py`, `verify_review_findings.py`, `diff_baselines.py`). |

`static/css/style.css`, `static/js/site-search.js` and `static/js/mobile-nav.js`
were in the writer's allowlist but are **deliberately untouched** — see §5.

The shell's colour is now expressed through the `--ps-shell-*` token family
(§11). Because the family is a set of aliases, every value quoted elsewhere in
this record still holds.

---

## 2. Composition as built

### 2.1 Every finish delta

Review finding F7 was right: the first version of this record claimed two
deliberate colour deltas when there were more. The complete inventory, which
is what the token step has to start from:

| # | Surface | Released | Now |
|---|---|---|---|
| 1 | Header ground | `#f6f7fa` | `var(--surface)` `#ffffff` |
| 2 | Header rule | `rgb(125 157 198 / 34%)` where a route was not already resolving `var(--border)` | `var(--border)` |
| 3 | Header shadow | `0 0.45rem 1.4rem rgb(10 27 54 / 10%)` | `none` |
| 4 | Brand pill | gradient + inset highlight + shadow | none |
| 5 | Brand artwork | portfolio shell added `saturate(1.18) contrast(1.08)` | shared drop-shadow treatment on every route; the logo FILE is untouched |
| 6 | Destination hover ink | `var(--accent-hover)` `#4a83e8` | `var(--ps-page-accent)` `#203767` — accessibility correction A1 |
| 7 | Active underline | `bottom: -4px`, radius 2px | seated 11px above the header rule, square. Colour unchanged |
| 8 | Search fill | `color-mix(--border 22%, --surface)` ≈ `#f7f9fb` | `var(--surface-soft)` `#f4f8fd` |
| 9 | Search radius / focus border | `999px` / `var(--accent)` | `0.5rem` / `var(--ps-page-accent)` |
| 10 | Results panel radius | `14px` | `0.75rem` |
| 11 | Menu toggle | `color-mix(--surface 88%, transparent)`, radius `0.6rem`, weight 700; expanded took an `--accent-soft` fill | `var(--surface)`, radius `0.5rem`, weight 650; expanded takes `--ps-page-accent` border and ink, no fill |
| 12 | Sheet ground | `color-mix(--bg-elevated 97%, transparent)` + `blur(24px)`, 18% shadow | `var(--surface)`, no blur, 12% shadow |
| 13 | Sheet states | hover/current ink and the current dot were `var(--accent)` `#0b63e5`; row radius `0.65rem` | `var(--ps-page-accent)` `#203767`; radius `0.5rem` |
| 14 | Phone bar, global structure only | frosted `color-mix` ground, `blur(26px) saturate(1.5)`, 14% shadow, current slot on an `--accent-soft` chip at weight 750 | flat `var(--surface)` under one rule, no frost or lift, current slot in `--ps-page-accent` ink with a 2px indicator |

None of these is a contrast regression; 6 is a correction. A page-owned
section-tab bar is deliberately excluded from 14 — its contents belong to that
room's package, not to this lane, so restyling it would change a surface this
writer does not own.

**Type is the released type, with two recorded exceptions.** The package does
not own the type scale, so destination size and weight stay at
`clamp(0.93rem, 0.85vw, 1.02rem)` / 620, the sheet rows stay at `0.92rem` / 650
with 750 for the current row, and no letter-spacing is introduced on any
released element. The exceptions:

1. The ACTIVE destination no longer jumps to 700 — see below.
2. `.platform-room-title` introduces `var(--font-serif)`, `1.05rem`, weight 600
   and `letter-spacing: 0.005em`. It is a NEW element with no released
   baseline, and the values match the board's phone header, but the earlier
   blanket claim that the active weight was the only type change was
   inaccurate. The bottom bar's slot label is likewise new type
   (`0.68rem` / 650), sized to fit four slots at 320px.

### 2.2 Composition

**Ground.** White (`var(--surface)` → `#ffffff`), one 1px rule
(`var(--border)` → `#d9e2ec`), `box-shadow: none`. The released header was
`#f6f7fa` with a `0 0.45rem 1.4rem` shadow. Header height stays `4rem`; the
existing breakpoint ladder is unchanged.

**Brand.** The logo file is untouched, at its released `2.2rem` height. What is
removed is the gradient glass pill drawn around it, plus the portfolio shell's
extra `saturate(1.18) contrast(1.08)` boost, so one logo treatment now renders
on every route in the artwork's own colours. Interview Studio's own accepted
visuals already set `.platform-brand__logo { background: transparent }`, so a
pill-less logo is precedent the owner has already seen.

**Destinations.** Five, unchanged, left-packed beside the logo rather than
`space-evenly` across the row. Each link is a 2.75rem box centred in the 4rem
row with `0 0.5rem` of horizontal padding. That geometry does three jobs at
once: a 44px target, a focus ring that wraps the label and stays inside the
header, and room for the underline to clear the header rule.

**Active state.** `aria-current="page"` → the room accent plus a 2px underline
via the same `::after` mechanism packages already override. Three decisions:

1. Weight no longer changes (620 → 700 previously), because that re-flowed the
   whole row on every navigation. Colour plus underline carry the state, at the
   released idle weight and size.
2. The colour is unchanged in computed value. The live cascade already resolved
   `--ps-page-accent` (`#203767`) through `body[data-room]`; the shell now
   *states* that rather than letting a room rule win by source position, which
   is architecture section 7.4's structural half achieved at zero pixel cost.
   Specificity is set deliberately above `body[data-room]` and deliberately
   below Interview Studio's page-scoped warm override, so that package's locked
   visuals still win. Measured and confirmed: `rgb(32, 55, 103)` before and
   after.
3. The underline is inset to the label, not the padded box, and its bottom edge
   sits 11px above the header's rule — direction 1's clearance normalised to
   this 65px header. Flush with the rule it read as a tab indicator fused to
   the chrome rather than an editorial underline.

**Account control (A3).** An initial from `identity.display_name` with the
existing "PeerSlate member" fallback, never a photo. Opens a labelled
disclosure holding only My Slate and Sign out. Keyboard operable, Escape
dismisses, outside pointer dismisses, focus returns to the trigger.

**Not built, by section 3.** No notification control — no notification route,
model or service exists. No Add/Capture control — `/app/capture` is owner-gated
behind a fail-closed allowlist. The Add position is reserved as a template
marker between search and the account control, shipping zero bytes, so the
future member contract is an insertion rather than a re-layout.

---

## 3. Responsive ladder as built

Measured with Playwright at 1440, 1280, 1100, 1024, 768, 743, 390, 320 and
720×450 (the 200% reflow of 1440×900), signed out and signed in, on `/`,
`/experience`, `/peerslate`, `/interview-studio`, `/opportunity-slate` and
`/petec/resume` — 6 routes × 9 viewports × 2 auth states. **No horizontal
overflow in any of the 108 probed states**
(`artifacts/2026-08-12-shell-editorial-top-bar/responsive_probe.json`).

> **Correction — the "6 routes" figure is inflated. Read §13.** Three of those
> routes return 404 locally, and the 404 template renders the shared shell, so
> those probes measured the shell on a 404 page rather than inside the room.

| Width | Built |
|---|---|
| ≥ 73.75rem | Logo · five inline destinations · search · account. One row, 65px including the rule. |
| 64.01–73.75rem | Room-switcher pill naming the current room, chevron, labelled list. **Search restored** — it was `display: none` in this band. |
| ≤ 64rem | Logo, or the room title where the viewer is signed in *and* the route is one of the five destinations. Search present at icon width, expanding in-row on focus. Account control. Menu, except on the signed-in routes where the global bottom bar renders. |
| ≤ 743px | The one bottom bar carries the global four slots for a signed-in viewer on a route with no section tabs. |
| ≤ 34rem | The existing `:has()`-scoped compaction block, kept — with sign out scoped out of it, see §9. |
| ≤ 22rem | Existing icon-only Menu behaviour, kept for every render that still shows the Menu. Where the global bar renders instead, the four slots fit 320px with no overflow and the Menu is redundant. |

**The room-title swap is server-driven and nothing else.** The row carries
`data-ps-shell-room-title` only when the server render is authenticated *and*
the route is one of the five destinations. No script ever writes that
attribute, so the brand cannot change after paint, and no `:has()` is
involved, so the behaviour is identical in every browser. It is deliberately
NOT keyed off `data-ps-auth-state`: `auth-state.js` rewrites that attribute
after its session probe, which would swap the brand mid-session. A stale
cached render simply keeps the logo, which is the released behaviour. The
homepage, `/experience` and `/peerslate` are not destinations, so they keep
the logo when signed in rather than leaving the brand slot blank.

Search is expanded in-row rather than as an overlay: an overlaid field at
390px would have covered the account and Menu controls and swallowed taps
meant for them. There is exactly **one** search field in the shell now — the
sheet's own copy is gone, because the header field is present at every width
and two visible inputs with the same accessible name is one affordance too
many.

---

## 4. The bottom-bar collision (architecture section 5)

**Resolved by making the global structure a source for the one existing bar,
not a second bar.**

`base.html` renders a hidden `[data-global-tabsource]` list — Pete's Slate,
Community, Interview — with real hrefs and server-set `aria-current`, **only
for a signed-in server render**. `public-mobile-nav.js` still prefers
`[data-mobile-tabsource]`; only where a page supplies none does it clone the
global list into `#mobile-tabbar` and append a More button. Consequences:

- Two fixed bottom bars are impossible by construction. Verified: exactly one
  full-width fixed `nav` at `bottom: 0` at 390px.
- A signed-out visitor gets no global bar and keeps the header Menu, which is
  what both approved boards draw for public phone navigation and what
  production does today. Verified at 320 and 390 signed out: no
  `[data-global-tabsource]`, no `has-global-tabbar`, Menu `display: flex`.
- All four slots fit 320px. Measured at 320: bar `clientWidth` 320,
  `scrollWidth` 320, every slot on screen, last slot ending at 312px. This
  matters because the bar sets `scrollbar-width: none`, so an overflowing slot
  would be both unreachable and silent.
- A page that owns its bar keeps every part of its released behaviour. Verified
  on `/petec/my-story`: slots are still `My Story / Slate Board / Résumé`, no
  More slot, no `has-global-tabbar`, header Menu still present.
- Both cases carry `body.has-mobile-tabbar`, so the bottom-padding contract is
  identical either way. Measured 58px at ≤743px on global-bar routes, 0
  elsewhere.
- Interview Studio's fixed composer already carried
  `body.has-mobile-tabbar.interview-studio-page .is__composer-actions
  { bottom: calc(3.9rem + safe-area) }`, so it lifts above the new bar with no
  edit to that package. Confirmed visually at 390×844.
- Where the global bar renders, the header Menu stands down at ≤743px: both
  opened the same sheet, and one affordance is the correct answer. Where a page
  owns the bar — and for every signed-out visitor — the header Menu is
  untouched.
- Where it carries the global structure, the bar takes the shell's language:
  a flat `var(--surface)` ground under one rule, no frost and no lift, and the
  current slot in `--ps-page-accent` ink with a 2px indicator instead of a
  tinted chip at weight 750. A page-owned section-tab bar keeps its released
  appearance exactly; its contents belong to that room's package.

Slot 1 keeps assumption A1's label "Pete's Slate" rather than the direction's
"Profile", for A1's own reason: no per-member profile route is registered and
labelling Pete's fixture portfolio "Profile" would make fixture content read as
shared product logic. Slot 3 shows "Interview" with
`aria-label="Interview Studio"` — the accessible name contains the visible text
(SC 2.5.3).

The alternative recorded by the architecture — moving section tabs inside each
room's content so the global bar is universal — remains a dependency for the
destination-stabilisation phase. It edits room-owned surfaces.

---

## 5. The public/owner fork: DEFERRED, with proof

**Architecture section 6 asks for convergence. It is not delivered, and the
blocking reason is measured, not assumed.**

`tests/test_owner_home.py::test_flag_off_app_render_is_byte_identical_to_existing_workspace`
locks `GET /app` to an exact byte length and SHA-256, and its normalization
chain asserts `pre_oppslate_nav_base.count(b"2b76a653fdca") == 1`. That literal
is the sha256[:12] content fingerprint of `static/css/style.css`, stamped into
every static URL by `_stamp_static_asset_version` in `app.py`. Verified in this
worktree:

```
static/css/style.css        2b76a653fdca   <- equals FLAG_OFF_STYLE_VERSION
static/js/site-search.js    8fcc302461af   <- inside the locked full-render hash
static/js/mobile-nav.js     1f0687c26f0b   <- inside the locked full-render hash
```

So **any** edit to `style.css` fails that test at the token assertion, and any
edit to `site-search.js` or `mobile-nav.js` fails it at the render hash — even
a whitespace change, and even though none of them alters `/app` markup. The
writer is explicitly forbidden from editing that test. Convergence therefore
cannot be delivered by this writer in this lane, because every route to it
either changes `/app` bytes or edits the lock:

- Deleting a duplicate and pointing `/app` at the survivor changes `/app`.
- Editing either duplicate in place changes `/app`.
- Loading `public-navigation.css` on `/app` changes `/app`.

A partial convergence *is* technically available — switching `/app/workshop`,
`/app/settings`, `/app/capture` and `/app/journal` to the public component set
while leaving `/app` alone. It is **not** taken here because it changes the
shell on four rooms owned by other packages (PS-WORKSHOP-001, PS-JOURNAL-001,
owner settings and capture) whose stylesheets and templates are outside this
writer's allowlist, so a collision could be caused but not corrected, and
because it would silently change owner search behaviour on those routes by
swapping `site-search.js` for `public-site-search.js`.

`tests/test_navigation.py::test_legacy_owner_workspace_keeps_the_unconverged_shell`
pins the deferral so it stays visible.

**The deferral is now user-visible.** The account menu's My Slate link, and the
More sheet's My Slate and Settings links, send a signed-in member from the
Editorial Top Bar into `/app*`, which still renders the old shell. Both routes
are real and member-scoped, so neither is a false affordance — but a member
crossing that boundary sees the header change under them. That is the concrete
cost of D1, and it is an argument for scheduling the convergence rather than
leaving it open indefinitely.

**To unblock:** a Protected change that recaptures the `test_owner_home.py`
golden values with the normalization proof the file's own comments require,
made by a writer authorized to edit that test, plus an owner decision on the
`/app/*` sub-path rooms.

---

## 6. Deviations from ARCHITECTURE.md

| # | Architecture text | Built | Why |
|---|---|---|---|
| D1 | §6 "Converge on one component set" | Deferred | §5 above — measured byte lock, forbidden test file. |
| D2 | §4 "≤ 64rem … Global bottom bar" | Bottom bar renders ≤743px | 743px is the released `.mobile-tabbar` visibility threshold in `style.css` and the width its padding contract keys to. §2 requires preserving that contract; a phone-style bottom bar at 1024px would also be wrong. The rest of the ≤64rem mobile structure is built as specified. |
| D3 | README "four-slot structure — Profile · Community · Interview · More" | Slot 1 is "Pete's Slate" | Assumption A1 governs the label, and its reason applies identically on a phone. |
| D4 | README "Workshop, Opportunity Slate, Settings, Help and Sign out under More" | No Help entry | No Help route exists anywhere in the application. Offering it would be a destination without a real page, which the package rules forbid. |
| D5 | §3 "Reserve the Add slot" | Reserved as a template marker, not reserved space | Reserving visible space for a control that does not exist would read as a defect. The marker fixes the insertion point without shipping bytes. |
| D6 | §7.4 "the shell's active state should resolve from `--ps-shell-accent`" | Resolves from `var(--ps-page-accent)`, stated once in the shell file | The `--ps-shell-*` family is the deferred token step. The structural half — the shell owning its active state instead of a room rule winning by cascade position — is delivered now at zero pixel cost. |
| D7 | §3 "an initial derived from `identity.display_name`" | Derived from `current_member.display_name` | `base.html` receives the principal, not the identity; `PeerSlatePrincipal.display_name` is the same claim-derived value with the same "PeerSlate member" fallback, and public chrome deliberately never wakes SQL for an account mapping. |
| D8 | §4/§5 imply the phone bottom bar is unconditional | Signed-in only | Both approved boards draw public phone navigation as hamburger, logo and Sign in with no bottom bar; production does the same today. Rendering it for a signed-out visitor also removed their hamburger, leaving Workshop, Opportunity Slate, Settings and the account controls reachable only through a hidden horizontal drag. Added in the review fix round. |
| D10 | README lines 44-46 and board 2 §C: More holds the OVERFLOW | More opens the header Menu sheet verbatim — all five destinations, repeating the three already in the bar, plus My Slate, Settings and Sign out | One sheet, one implementation, one destination list, and no second overlay to keep in step. The cost is real and is recorded rather than argued away: the sheet is a top-anchored panel under a sticky header, which is what made §12 F-A possible. A bottom-sheet card holding overflow only would not have had that failure mode. |
| D9 | §4 "keep the existing breakpoints … do not introduce a parallel set" | One rule block at ≤743px | 743px is the released `.mobile-tabbar` visibility threshold already in `style.css`, and the width its padding contract keys to. Not a parallel ladder — the same existing breakpoint the bar has always used. |

---

## 7. Accessibility corrections (recorded individually, measured)

**A1 — destination hover/focus ink.** Was `var(--accent-hover)` → `#4a83e8`:
**3.68:1** on the new `#ffffff` ground and **3.46:1** on the released `#f6f8fc`
ground. Both fail SC 1.4.3 (4.5:1). Now `var(--ps-page-accent)` → `#203767`:
**11.64:1**. This is the ink the active state already used, so hover and
current now read as one family.

**A2 — WITHDRAWN.** The first version of this record claimed a focus-offset
correction: `outline-offset` went from the site's `4px` to `-3px` because the
links were the full height of the row. The review measured the result and it
was worse than the problem — a 3px ring drawn *inside* the text box, clipping
the first and last glyphs, in a 58px-tall box around a 15px label. The offset
override is gone. The links are now a 2.75rem box centred in the 4rem row with
`0 0.5rem` of padding, which lets the untouched site ring wrap the label
cleanly and stay inside the header. **No focus value is changed by this
package at all**; §7.3 keeps the whole focus question.

Measured after: ring 3px..61px inside a 0..65px header, 12px of clearance
between the ring and the nearest glyph.

**Non-text contrast, observed and NOT resolved here.** `--border` `#d9e2ec` on
`#ffffff` is **1.31:1**, so the search field's boundary is below SC 1.4.11's
3:1. The released control had the same weakness. The field keeps a soft
`var(--surface-soft)` fill so the boundary is at least as readable as before,
but the border value is a palette decision owned by the Colour, Background and
Typography Audit. Recorded, not silently invented.

---

## 8. Verification

Focused suites, project venv, placeholder key:

```
tests.test_navigation tests.test_auth tests.test_search_visibility
    Ran 66 tests — OK
tests.test_owner_home
    Ran 25 tests — OK   (the /app byte lock survives every base.html edit)
```

Adjacent suites that couple to the shell, all green:
`test_signin_experience` · `test_homepage_scenes` · `test_site_rules` ·
`test_community_tabs` · `test_workshop_checkpoint` · `test_opportunity_slate_v2`.

Browser verification (`artifacts/2026-08-12-shell-editorial-top-bar/`):

- `verify_shell_interaction.py` — 37 of 38 checks pass. The one failure is
  `/auth/session` returning 503 because a local run has no database;
  `auth-state.js` handles 503 by preserving the server-rendered controls, and
  the same 503 occurs on this branch's base.
- `responsive_probe.json` — computed geometry and visibility for every
  route × viewport × auth state.
- `review_fix_measurements.json` — the before/after numbers for the review's
  six MUST-FIX findings, reproduced by `verify_review_findings.py`.
- `baseline/` — 150 frames plus `DIGESTS.json`. **This is the pre-tokenization
  baseline** the token step must diff against. 62 of those frames are OPEN
  states: account menu, More sheet, room-switcher list, search results, the
  honest search-empty state, hover, keyboard focus, and 200% text. A baseline
  of closed-shell crops alone would have been blind exactly where the shell's
  colour lives — which is where the sign-out sizing defect was hiding.

Both browser scripts drive two servers: 5057 signed out, and 5058 with the
development identity so the SERVER renders signed in. The shell's signed-in
markup is server-derived, so faking it in the DOM does not exercise the real
render.

Keyboard order asserted (not merely printed) at 1440: skip link → logo → the
five destinations → search → Sign In → page content. Escape dismisses both
disclosures and the More sheet, and focus returns to the control that opened
each.

### 8.1 Review fix round — measured before and after

| # | Before | After |
|---|---|---|
| F1 bottom bar at 320 | bar `clientWidth` 320 / `scrollWidth` 344; More ran x=280.8→335.5, 15.5px off screen behind a scrollbar-less overflow; header Menu hidden | `clientWidth` 320 / `scrollWidth` 320; slots 8→84, 84→160, 160→236, 236→312; nothing off screen. Signed out there is no bar at all and the Menu stays |
| F2 Sign out in the menus | 11.52px in a 32px box, beside neighbours at 15px/44px | 14.72px in a 44px box in both menus, identical to My Slate and Settings, at 320 and 390 |
| F3 signed-out phone | bar present, `menuToggle` `display: none` | no `[data-global-tabsource]`, no `has-global-tabbar`, `menuToggle` `display: flex` |
| F4 underline clearance | 1px above the header rule | 11px above the rule; underline bottom edge 54px in a 65px header, still 2px, still `rgb(32, 55, 103)` |
| F5 nav focus ring | `outline-offset: -3px` drawn through the label, clipping glyphs, ring −7px..51px against a 0..65px header | site default `4px` offset restored; ring 3px..61px, inside the header, 12px clear of the nearest glyph |
| F6 search fields | two visible with the sheet open (`nav-search-input` + `nav-search-input-mobile`) | one input in the whole document; one results panel; one `aria-label="Search PeerSlate"` |
| F8 destination type | idle 15px/500, active 15px/500 (released: 14.88px/620 and 700) | idle and active both 14.88px/620, `letter-spacing: normal` — released values, minus the active-state weight jump |

## 9. The Interview Studio byte lock: resolved, not outstanding

**This section previously said the lock "fails: 114728 != 111406" and needed
another lane's writer. Both statements are out of date. The lock passes.**

`tests/test_interview_studio.py::InterviewStudioFlagOffByteComparabilityTests`
locks the byte length and normalized sha256 of the anonymous
`/interview-studio` and `/interview-studio/history` renders. Both pages render
the SHARED global shell, so any shell markup change fails that lock by
construction. It was never an Interview Studio regression.

What actually happened:

1. The package scope was **amended under an owner-authorized scope limit** to
   permit recapturing exactly these four constants — nothing else in that file.
2. That the delta is shell markup only was established independently rather
   than asserted: the same route was rendered with the BASE `base.html`
   injected through a Jinja `ChoiceLoader`, touching no file, and the two
   documents became byte-identical once the `<header class="global-header">`
   block and the `<ul class="global-tabsource">` list were replaced with
   placeholders. Nothing in the Interview Studio body changed.
3. The constants were recaptured **three times** as the shell settled — after
   the tokenization, after the pre-merge fixes, and again after the rebase —
   using `artifacts/2026-08-12-shell-editorial-top-bar/recapture_interview_bytelock.py`,
   which only prints values and changes nothing.

**The final digests were captured from a clean git checkout, and that matters.**
The render embeds each stylesheet's `?v=` content fingerprint, which is a hash
of the file's bytes on disk. On this Windows worktree those bytes carry CRLF
line endings; git normalizes them to LF on commit, so a fingerprint taken over
a dirty or unnormalized working tree is not the fingerprint the committed tree
produces. Capturing with the tree clean — every shell file committed and
checked out — is what makes the recorded constants the ones the test will
recompute for any other checkout of the same commit.

The recapture is therefore complete and in scope. It is not owed to anyone.

## 10. Not delivered

- Public/owner shell convergence (§6) — see §5.
- Real-tablet behaviour reported separately from resized desktop. The
  touch-tablet viewport script is preserved untouched, but a genuine iPad
  forces the 1280px desktop viewport, which is a different code path from a
  resized browser and has not been exercised on hardware.
- Cross-route verification beyond the six routes probed.

---

## 11. Tokenization (architecture section 7)

The shell now resolves its colour through a namespaced `--ps-shell-*` family
that aliases the production variables it already used. **Measured inert: all
150 baseline frames unchanged.**

### 11.1 The family, and where it is declared

```css
.global-header,
.mobile-tabbar {
    --ps-shell-ground:      var(--bg);
    --ps-shell-stage:       var(--bg-elevated);
    --ps-shell-surface:     var(--surface);
    --ps-shell-rail:        var(--surface-soft);
    --ps-shell-border:      var(--border);
    --ps-shell-text:        var(--text);
    --ps-shell-text-muted:  var(--text-muted);
    --ps-shell-accent:      var(--accent);
    --ps-shell-accent-soft: var(--accent-soft);
    --ps-shell-accent-room: var(--ps-page-accent);   /* §7.4 exception */
    --ps-shell-focus:       var(--color-gold-bright);/* §7.3 honest name */
}
```

**This is declared on the shell's roots, not on `:root`, and that is a
deliberate correction to §7.1.** Section 7.1 writes the block at `:root`. At
`:root` it causes precisely the silent repaint the section exists to prevent,
because custom properties substitute at computed-value time on the element the
declaration applies to: `--ps-shell-surface: var(--surface)` written at `:root`
freezes to `:root`'s `--surface` and inherits that frozen value straight past
every later redefinition on `<body>`.

I implemented it at `:root` first and measured it rather than asserting it.
On `/`, `/experience`, `/peerslate` and `/interview-studio`:

| Token | Production value (live) | Token value at `:root` |
|---|---|---|
| surface | `#ffffff` | `#1c2528` |
| border | `#d9e2ec` | `rgb(255 255 255 / 14%)` |
| rail, text, accent | live light values | all frozen dark-era `:root` values |

That is a near-black header on every page. Declared on `.global-header` and
`.mobile-tabbar` — both direct children of `<body>` — each alias resolves
against the value that element has actually inherited through
`:root` → `body[data-theme="modern-blue"]` → `body.slate-light`, which is what
makes the substitution inert. Every other shell surface (`.platform-menu`, the
account menu, the switcher list, the search panel) is a descendant of
`.global-header`, so it inherits the tokens.

Verified directly, not only by screenshot: **all 11 aliases resolve identically
to their production variable on 6 routes × 2 auth states**, on both
`.global-header` and `.mobile-tabbar`.

### 11.2 Which token owns the active state

`--ps-shell-accent-room`, aliasing `--ps-page-accent`. **Not**
`--ps-shell-accent`.

§7.4 wants the active state resolving from the shell family with room tint as
an explicitly scoped exception. Both halves are now satisfied, but not by
moving the value: `--ps-page-accent` is `#203767` and `--accent` is `#0b63e5`,
so pointing the active state at `--ps-shell-accent` would repaint every active
destination on every route. The instruction was explicit — if moving it changes
a computed value, do not move it — so it did not move.

What changed is that the exception is now *named and one line long* instead of
implicit. The audit points `--ps-shell-accent-room` at `var(--ps-shell-accent)`
and the shell's active state becomes the shell accent, everywhere, in one edit.
That closes deviation D6 as far as it can be closed without a palette decision.

### 11.3 Focus (§7.3)

**Measured first, then aliased. No visual change.**

The live ring is `3px solid var(--color-gold-bright)`. That variable is
`#ffd36a` at `:root` and `#4a83e8` under `body[data-theme="modern-blue"]` — a
blue ring from a variable named gold, which is exactly why §7.3 asks for an
honest name.

SC 1.4.11 needs 3:1 for non-text. Measured `#4a83e8`:

| Against | Ratio | Result |
|---|---|---|
| `--bg` `#fdfdfe` (the §7.3 test) | **3.62:1** | passes |
| `#ffffff`, the ground the ring is actually drawn on | **3.68:1** | passes |

It passes, so `--ps-shell-focus` is a pure alias and **the authorized visual
correction was not needed and not taken**. The shell now states its own ring
(`outline: 3px solid var(--ps-shell-focus)`) on its own focusable controls, at
the same computed colour, width and offset as the site rule it restates — the
four `nav-focus` frames are identical, which is the proof. It exists so the
Colour audit has one named place to change the shell's ring.

Combined with the withdrawn A2, this package changes **no focus value at all**;
it only gives the existing one a truthful name.

### 11.4 Not aliased, recorded instead

Three production references remain live in shell rules:

- `var(--shadow)` — three uses (switcher list, account menu, search results).
  The §5 family does not name a shadow role, and inventing one would exceed the
  package's stated token contract. **Superseded by §14.4:** the owner asked for
  every shell colour to resolve one way, a shadow is colour, and the More
  sheet was carrying a fourth, bespoke value. The role is now named
  `--ps-shell-shadow` and all four panels take it.
- `var(--font-serif)` — the phone room title. Type belongs to the audit.
- `var(--accent-hover)` — survives only inside a comment, not in any
  declaration.

`--ps-shell-ground` and `--ps-shell-stage` are defined but currently unused by
shell rules: the shell paints on `--ps-shell-surface`, and the frosted grounds
that used `--bg-elevated` were removed earlier in this package. They are
defined because §5 names them as part of the family the package promises.

`static/css/design-system/tokens.css` is **not** adopted. It is an unadopted
parallel `--ps-*` system whose values differ from live (`#f7faff` vs `#fdfdfe`,
`#4ea3ff` vs `#0b63e5`), so aliasing to it would repaint. Divergence recorded,
not resolved here.

No `@media (prefers-color-scheme)`, no second value set, no theme-switching
scaffolding. Flat values, light only.

### 11.5 The proof (architecture section 8) — and a correction

**The frame diff I first reported was produced by a broken comparison. The
tokenization is inert, but the earlier numbers were not evidence of it.**

`diff_baselines.py` compared frames with
`ImageChops.difference(a, b).getbbox()` on RGBA images. Pillow's `getbbox()`
takes an `alpha_only` argument that **defaults to True**, so it inspected only
the alpha channel — and two fully opaque screenshots always have an identical
alpha channel. It returned "identical" for a frame pair with 167 differing
colour pixels. Every "N pixel-identical" figure in the earlier rounds came from
that path and should be disregarded. The tool now compares RGB channel extrema,
which has no such trapdoor.

With the corrected tool, the frame method turns out to be unusable as a gate
here at all. Capturing the **same** stylesheet twice produces ~22 differing
frames, several with thousands of pixels and a 249 channel delta — font
rasterisation and interaction timing move between runs. A frame diff cannot
separate a real regression from that noise, so a "150 of 150 identical" claim
was never available by this method, before or after the fix.

**The definitive proof is by computed style**, which has no noise floor.
`verify_tokenization_computed.py` snapshots every CSS property of every node
under `.global-header` and `#mobile-tabbar`, swaps the stylesheet for its
de-tokenized twin **in the same live DOM**, snapshots again, and diffs.
Transitions are neutralised first, because swapping a stylesheet restarts them
and a mid-transition snapshot reports an interpolated value — an artifact of
the method, not of the change. Custom properties are excluded on purpose:
`--ps-shell-*` existing in one variant and not the other is the change itself.

| | value |
|---|---|
| states compared (route × auth × viewport × open state) | **174** |
| node snapshots taken | **18,118** |
| **non-custom-property deltas** | **0** |

Before transitions were neutralised the run reported 46 deltas, every one of
them `width`, `transform`, `transform-origin`, `perspective-origin`,
`inline-size` or `grid-template-columns` on the animating chevron and the
width-transitioning search field, at sub-pixel magnitudes. **Zero colour or
paint properties moved in either run** — the property that matters for a colour
token layer never differed at all.

This is the same method the independent pre-merge review used, and it reached
the same result independently.

**Provenance.** Two servers drive every capture, and a mispointed one would
silently invalidate the comparison — this happened once, when a restarted
server was found serving a *different checkout*'s stylesheet. Both are now
pinned to the worktree and token-checked against the on-disk file before every
capture.

**The frame set is kept as a visual record, not as a gate.**
`artifacts/2026-08-12-shell-editorial-top-bar/baseline/` holds 150 frames of
the shell as it now stands, including 62 open states. Treat a frame difference
as a prompt to look, not as a failure.

---

## 12. Pre-merge review round

Nine findings fixed, two recorded. Measurements in
`artifacts/2026-08-12-shell-editorial-top-bar/premerge_fix_measurements.json`,
reproducible with `verify_premerge_findings.py`.

### F-A (HIGH) — sheet rows unreachable on a landscape phone

The sheet is `position: absolute` under a `position: sticky` header, so its
bottom edge is pinned to the viewport and scrolling the page could not bring a
row below the fold into view. Signed in it is ~372px tall; the account group
this package added is ~101px of that, which is what pushed it past the fold.
It now carries its own scroll, bounded to the space under the header.
`100dvh` rather than `100vh` so a retracting mobile URL bar cannot hide the
last row.

| Viewport | Before — unreachable | After — unreachable by scrolling | by keyboard |
|---|---|---|---|
| 390×400 | Sign out | **none** | **none** |
| 568×320 (iPhone SE landscape) | My Slate, Settings, Sign out | **none** | **none** |
| 640×360 (Android landscape / 1280×720 at 200% zoom) | Settings, Sign out | **none** | **none** |
| 320×256 (SC 1.4.10 Reflow) | four rows | **none** | **none** |

Rows still sit below the fold at rest — that is what a scrollable panel is —
but every one is reachable by scrolling the sheet, and focusing a row scrolls
it into view on its own. The measurement checks both, because the released
failure was precisely that neither worked.

### F-B — a signed-in phone lost navigation while scrolling

Scroll-away belongs to a section-tab bar, where the header Menu is still on
screen. The global bar stands the Menu down, so hiding it left a signed-in
phone with no destination navigation at all. The global bar no longer
auto-hides. Measured at 390×844 signed in, after scrolling: `is-hidden` false,
bar on screen, four slots reachable. A page-owned section-tab bar keeps its
released scroll-away exactly.

### F-C — the tokenization commit was not a pure substitution

It added a focus rule alongside the aliases. At (0,2,1) that rule outranked
`.theme-toggle:focus-visible` (0,2,0), stacking a third ring on a control that
draws its own — invisible to 150 frames because the toggle is flag-gated off.
It also outranked the dormant dark `:where(a,button,…):focus-visible` reset,
contradicting this file's own header. Both are now guarded:
`body:not([data-theme="dark"])` on every clause, and `:not(.theme-toggle)` on
the button clause. The bar rules took the same dark guard.

### F-D — the bottom bar was the thinnest navigation on the site

Text-only 31.8px slots, against 2.75rem everywhere else this package touches.
Now icon above label, `min-height: 2.75rem`, measured **44.5px** at every
width. The current slot takes the board's treatment — a **filled** mark plus a
coloured label — and the 2px top indicator, which was an invention, is gone.
Measured on `/interview-studio` signed in: current slot `fill:
rgb(32, 55, 103)`, `stroke: none`, label `rgb(32, 55, 103)`, `::before content:
none`. The bar draws from its own closed-path icon set, because an open stroke
path cannot be filled.

### F-F — underline geometry against the board

"Board 3" in an earlier version of this row meant the third approved board,
`GLOBAL_SHELL_PUBLIC_MEMBER_OWNER.png`. It reads as Direction 3 — the rejected
`03_adaptive_room_rail_REJECTED_FOUNDATION.png` — which it never meant. Boards
are named in full here and in `public-navigation.css` from 2026-08-13.

| | `GLOBAL_SHELL_PUBLIC_MEMBER_OWNER.png` (normalised to a 65px header) | Before | After |
|---|---|---|---|
| overhang each side | ~8px | 0 | **8.0px / 8.0px** |
| thickness | 5.0% of header | 2px (3.1%) | **3px (4.6%)** |
| clearance above the rule | ~11px | 11px | **11px** |

`right/left: 0` lands on the link's padded box, which is the label plus this
package's existing 0.5rem padding — so the overhang falls out of the geometry
rather than being a second magic number.

### F-G — 200% text overflowed by 4px

A media query's `rem` is the **initial** root font size, not the current one,
so the width-keyed ladder can never collapse the row as text grows. The row now
wraps, which is the reflow answer: it grows taller and nothing is lost.

| | Before | After |
|---|---|---|
| document scroll width at 1440 | 1444 (4px overflow) | **1440 (0px)** |
| last destination | x 1155→1444, off screen | x 433→722, wrapped to row 2 |
| header height | 65px | 265px, both auth states |

Inert at 100%: the row has room and never wraps.

### F-H — an accessible name that announced a room that did not exist

On `/`, `/experience` and `/peerslate` the switcher read "Browse destinations,
current: Browse". The "current:" clause is now conditional, and those routes
read simply "Browse destinations". Deliberately structured so the rendered
bytes on a route that HAS a room are unchanged — see §12.1.

### F-I — a bfcached signed-in page kept a member bar after sign-out

The global bar is a signed-in affordance and it hides the header Menu, so it
must not outlive the session. A `MutationObserver` on the server-derived
`data-ps-auth-state` tears the bar down and restores the Menu whenever the
state leaves `authenticated` — covering bfcache restore, session expiry, and a
sign-out in another tab. Nothing protected leaked before this: all four slots
are public routes.

### 12.1 The Interview Studio byte lock, recaptured

Every round of shell CSS work re-triggers this lock, because the render
carries `public-navigation.css`'s `?v=` content fingerprint and the test
normalizes only the Interview JS token. Each time, the stylesheet token was
shown to be the ONLY delta before the constants were touched:

- the anonymous `/interview-studio` HTML was **byte-identical** before and
  after the template edits, rendered both ways and compared directly;
- byte length stayed at the locked value;
- normalizing **only** the `public-navigation.css` token back to its previous
  value reproduced the locked sha exactly.

No Interview Studio markup, layout, destination or control semantics changed
in any round. The recapture was authorized by the amended package scope, is
limited to these four constants, and is complete — see §9. The digests
themselves are the four constants in tests/test_interview_studio.py.

### 12.2 Final re-verification after the truth-correction pass

The last pass edited stylesheet comments and split the phone-bar rules so
layout could stay unguarded while colour kept its dark guard. Moving
declarations between sibling rules is the class of change that is usually
inert and occasionally is not, and "the tokenization is inert" is this
package's central claim, so it was measured rather than assumed. Both proofs
are by computed style; the frame set is a visual record only.

| Proof | Scope | Result |
|---|---|---|
| Tokenization still inert (`verify_tokenization_computed.py`) | 174 states, **18,118** node snapshots | **0** non-custom-property deltas |
| The revision itself inert (`verify_css_revision_inert.py cb9d000`) | 40 states, **4,055** node snapshots | **0** deltas, custom properties **included** |

The second compares the current stylesheet against the one immediately before
the pass, swapped into the same live DOM. Custom properties are included there
because that revision was not supposed to change them either.

**Light theme only, and confirmed so.** Every state asserts that `<body>` does
not carry `data-theme="dark"` before snapshotting, and the assertion held for
all 40. Dark cannot render — `PEERSLATE_DARK_THEME_ENABLED` is off — so what
had to be proven is that the render which actually ships did not move.

**The split's own rules, checked property by property.** The elements the split
touched were observed 90, 60 and 60 times respectively, and every watched
property matched — 2,550 comparisons, no exceptions:

| Element | Instances | Properties confirmed identical |
|---|---|---|
| `.mobile-tabbar__item` | 90 | `display`, `min-height`, all four paddings, `font-size`, `font-weight`, `flex-direction`, `align-items`, `justify-content`, `gap`, `flex-grow/shrink/basis`, `line-height`, `text-align`, `color`, `background-color` |
| `.mobile-tabbar__label` | 60 | `display`, `max-width`, `overflow-x/y`, `text-overflow`, `white-space`, `color`, `font-size` |
| `.mobile-tabbar__mark` | 60 | `width`, `height`, `fill`, `stroke`, `stroke-width`, `flex-shrink` |

The layout half of the split therefore resolves identically unguarded, which
is what makes the narrowing safe: dark inherits the structure and overrides
only the ink. No CSS change was forced by either proof, so the byte-lock
digests in §12.1 stand unrecaptured.

### 12.3 Known limitation: five destinations at 200% text

Recorded rather than fixed, on the review's instruction, because fixing it
properly means collapsing the ladder on CONTENT width rather than viewport
width — a real design change that belongs in its own round.

The F-G fix made the destination row wrap so that growing text loses nothing.
With `PEERSLATE_WORKSHOP_ENABLED=true` the row carries five destinations, and
at 200% text each one takes its own line. Measured on `/interview-studio`,
Workshop flag on:

| Viewport | 100% header | 200% text header | Rows | Overflow |
|---|---|---|---|---|
| 1200×800 | 65px (8.1%) | **441px (55.1% of viewport)** | 5 | 0px |
| 1280×800 | 65px (8.1%) | **441px (55.1%)** | 5 | 0px |
| 1366×768 | 65px (8.5%) | **441px (57.4%)** | 5 | 0px |
| 1440×900 | 65px (7.2%) | 353px (39.2%) | 4 | 0px |

No content is lost and horizontal overflow stays 0 at every width, so
SC 1.4.4 Resize Text and SC 1.4.10 Reflow are both met. A sticky header
occupying 57% of a 1366×768 viewport is a quality problem, not a conformance
one.

**Every other 200% measurement in this record was taken flag-off, with four
destinations.** Production may serve five. The flag-off figures are therefore
the optimistic case, and this table is the one to read for the shipped
configuration.

---

## 13. Correction: three "routes" were 404 pages carrying the shell

Found by the implementation writer while verifying a claim for the independent
review record rather than repeating it. It corrects this document's own
evidence, so it is recorded here rather than only there.

Measured directly against the local application:

| Route | Local status | Renders the shared shell? |
|---|---|---|
| `/` | 200 | yes |
| `/interview-studio` | 200 | yes |
| `/petec/resume` | 200 | yes |
| `/experience`, `/peerslate` | 200 | yes |
| `/opportunity-slate` | **404** | **yes** |
| `/the-slate` | **404** | **yes** |
| `/app/workshop` | **404** | **yes** |

The 404 template extends `base.html`, so a 404 response still carries
`.global-header`, the full `.platform-nav__links` list and a correct
`aria-current` — the nav sets that from `request.path`, which matches whether
or not the room resolves. That is why the probes and frame captures on
`/opportunity-slate` produced entirely plausible shell measurements: the shell
really was rendering. It was rendering **on a 404 page**, not inside the
Opportunity Slate room.

**What this does and does not invalidate.** The shell geometry, overflow,
account, switcher, search and underline measurements stand — the shell under
test was the real shell. What does not stand is any implication that the shell
was exercised *inside* Community, Opportunity Slate or Workshop. It never was.
Route counts in §3 and the four-route frame baseline should be read with that
correction: three real pages, one 404-with-shell.

**`/the-slate` is the material gap.** It is the only route besides `/petec/*`
that owns its own mobile tab bar via `[data-mobile-tabsource]`, and the whole
§4 resolution — one bar, page-owned behaviour preserved, the global structure
cloned only where a page supplies no section tabs — turns on exactly that
interaction. It was proven on `/petec/my-story`, which owns a section-tab bar
and correctly kept its own slots, its header Menu and no `has-global-tabbar`.
**It was never proven on Community.** Until `/the-slate` resolves locally or
the shell is seen there on a live environment, the one-bar resolution is
verified on one of the two routes it governs.

Workshop carries a second, smaller unknown: `/app/workshop` is an `/app*` path,
so it takes the unconverged legacy owner shell (§5) rather than the Editorial
Top Bar at all.

---

## 14. Owner round 2, 2026-08-13 — the mark, four findings, and shell colour

Pete looked at rendered screenshots of this shell for the first time and asked
for a further round. This section records it. **It has not been independently
reviewed** — the three rounds in `INDEPENDENT_REVIEW.md` all predate it.

### 14.1 The priority: the logo is always revealed

> "logo should always be revealed ... It should always be revealed."

He named **768–1024 signed in**. Measured on the running application before the
change, that is exactly right, and the band is wider than he saw: at **every**
width at or below 64rem, a signed-in viewer inside one of the five destinations
lost the mark completely. `.platform-brand__logo` was `display: none` and
`.platform-room-title` was drawn in its place.

Measured, signed in, on `/interview-studio`, `/opportunity-slate` and
`/petec/resume` (the img's own box, `getBoundingClientRect`):

| Width | Before | After | Signed out, before and after |
|---|---|---|---|
| 1024 | `display: none`, 0 × 0 | **121.6 × 26.4 at x = 20.5** | 121.6 × 26.4 at x = 20.5 |
| 900 | `display: none`, 0 × 0 | **121.6 × 26.4 at x = 18** | 121.6 × 26.4 at x = 18 |
| 768 | `display: none`, 0 × 0 | **121.6 × 26.4 at x = 16** | 121.6 × 26.4 at x = 16 |
| 743, 600, 544, 390, 320 | `display: none`, 0 × 0 | **121.6 × 26.4 at x = 16** | 121.6 × 26.4 at x = 16 |
| 1440, 1280, 1100 | 176.4 × 35.2 | unchanged | unchanged |

The signed-in mark is now geometrically identical to the signed-out mark at
every width. Nothing was shrunk to achieve it: the released
`height: 1.65rem; width: 7.6rem; object-fit: contain` mobile box and the
released 2.2rem desktop height are untouched, and `elementFromPoint` at the
img's centre returns the img itself in every state, so it is painted rather
than merely laid out. Horizontal overflow stays 0 at all eleven measured widths
in both auth states.

**The room title now sits beside the mark**, behind a 1px `--ps-shell-border`
divider with 0.75rem of padding, from 34.01rem to 64rem. Below 34rem it stands
down and the mark stays — the owner's stated order of sacrifice. Measured with
the longest label, "Opportunity Slate", at the narrow end of its band: at 545px
the title occupies 148.6px starting at x = 149.6, the actions column starts at
x = 453.8, and `scrollWidth == clientWidth` on the title, so nothing truncates.
At 390 the same label would have had 149.2px of room against 148.6px of text —
a 0.6px margin, which is a coincidence rather than a fit, and it clips outright
on a 375px phone. 34rem is an existing rung of this file's ladder, not a new
one.

**The title is turned ON inside a band, not turned off below one**, and that
shape was forced by a real contract rather than chosen for tidiness. The first
attempt hid it with a `display: none` inside the existing `@media (max-width:
34rem)` block, and `tests/test_signin_experience.py::HeaderOverlapFixTests`
correctly failed it twice: PS-SIGNIN-EXPERIENCE-001 reserves that block for
sign-out-scoped compaction, forbids any rule there that removes a header
control, and checks every selector in it individually. That test is not in this
writer's allowlist and was not touched. `.platform-room-title` is already
`display: none` by default at the top of the file, so a
`@media (max-width: 64rem) and (min-width: 34.01rem)` band turns it on where it
fits and nothing anywhere turns it off. Behaviour measured identical before and
after the restructure at 1024, 900, 768, 743, 600, 545, 544, 390, 375 and 320.

**This diverges from the approved boards and the divergence is deliberate.**
`01_editorial_top_bar_LEADING_NOT_LOCKED.png` C and
`02_room_switcher_MEDIUM_WIDTH_REFERENCE.png` C both draw the signed-in phone
header with the room name **instead of** the mark, and ARCHITECTURE.md §1
listed that as authority. README's pixel rule settles it: where a board and the
owner's written direction disagree, the direction wins and the divergence is
recorded. It is recorded in README, in `public-navigation.css`, and here.

The fix is **CSS only**. `base.html`'s rendered bytes are unchanged — the one
template edit is inside a Jinja comment, which never reaches the response — so
the Interview byte-lock LENGTHS could not move, and did not.

`tests/test_navigation.py::test_the_logo_is_revealed_at_every_width_in_every_auth_state`
guards the regression where it actually lived. A markup assertion could never
have caught this: the template always emitted the logo, and a stylesheet rule
removed it. The test therefore parses the stylesheet's declaration blocks and
fails if any selector naming `platform-brand__logo` carries `display: none`,
`visibility: hidden` or `content-visibility: hidden`, and separately asserts
that the only thing the 34rem block removes from the brand row is the room
title.

### 14.2 Finding F1 — the phone bar's parent rule was still mixed

The file's own header states the principle: colour guarded, layout unguarded.
The `.mobile-tabbar__item` rule was split that way in the previous round; its
parent `.mobile-tabbar` rule was not, so `gap`, `padding` — including
`env(safe-area-inset-bottom)` — and `overflow-x` were sitting inside the
`:not([data-theme="dark"])` colour guard.

Split the same way, and for the same measured reason: the dormant
`body[data-theme="dark"] .mobile-tabbar` rule in `style.css` redefines
`background`, `border-top`, `box-shadow` and `backdrop-filter` and nothing
else, so those four are all the guard has to protect, and the geometry has no
dark counterpart to collide with. Layout now sits at (0,2,1) unguarded; colour
stays at (0,3,1) guarded.

Proven inert by computed style: across 60 states the four bar elements were
observed 60 / 130 / 100 / 100 times and **4,684 watched property comparisons
were identical**, including `.mobile-tabbar`'s own `gap`, four paddings,
`overflow-x`, `background-color`, `border-top`, `box-shadow`,
`backdrop-filter`, `position` and `z-index`.

### 14.3 Finding F2 — the current room had no persistent fill

`02_room_switcher_MEDIUM_WIDTH_REFERENCE.png` section B draws a soft persistent
fill behind the current row. Sampled off the board: the current row runs
`rgb(243, 246, 244)` against a `rgb(254, 254, 254)` panel ground, about a 4%
drop, across its full height (y ≈ 605–648 in the 923 × 1704 export).

The released rule gave that row accent ink and weight 750 but a background only
on `:hover` and `:focus-visible`, so at rest it was indistinguishable from every
other row — and the More sheet's current row, which does fill, disagreed with it
about what "current" looks like.

Both now take `--ps-shell-accent-soft`. The board's own value is a green-tinted
grey and is **not** adopted: README's pixel rule keeps production colour and
this package selects no palette.

### 14.4 Shell colour consistency — one role, one value

The instruction was to make the same semantic role resolve to one value
throughout the shell, and to stay strictly inside shell scope. Six things were
found. Each is a real computed-value change.

**1. One soft-fill role.** A hovered or current row in the room switcher, the
account menu and the More sheet is the same thing. The switcher's rows used
`--ps-shell-rail`; everything else used `--ps-shell-accent-soft`. Rail is the
shell's *control* ground, so one token was carrying two roles and one role had
two values. Rail keeps the controls; accent-soft keeps the rows.

**2. One control ground.** The search field, the switcher pill and the account
trigger all sat on `--ps-shell-rail`; the Menu button sat on
`--ps-shell-surface`. Three compact controls in one row, two grounds. The Menu
button joins its neighbours.

**3. One menu-row ink.** The More sheet's account rows — My Slate, Settings,
Sign out — were `--ps-shell-text-muted`, while the *identical* My Slate and
Sign out in the account menu, and every destination row in the same sheet, were
`--ps-shell-text`. Measured on the sheet's `#ffffff` ground: 17.26:1 against
6.41:1. Both pass SC 1.4.3; now they also match.

**4. One panel elevation.** The switcher list, the account menu and the search
results resolved `var(--shadow)`; the More sheet carried a bespoke
`0 1rem 2rem rgb(10 27 54 / 12%)`. The role is now named `--ps-shell-shadow`
and all four take it. Measured on the open sheet:
`rgba(10, 27, 54, 0.12) 0px 16px 32px 0px` becomes
`rgba(6, 26, 58, 0.08) 0px 12px 30px 0px`.

**5. One palette on every route — the big one.** The `--ps-shell-*` aliases
resolve against whatever context the page's `<body>` supplies, and `base.html`
gives every route `body.slate-light` **except `/experience`**. There the chain
stops at `body[data-theme="modern-blue"]` and the same global chrome painted a
different palette. Measured signed out and signed in at 1440 / 900 / 390 across
eight routes:

| Token | Seven routes | `/experience` |
|---|---|---|
| `--ps-shell-border` | `#d9e2ec` | `#e5e7ec` |
| `--ps-shell-text` | `#061a3a` | `#16213a` |
| `--ps-shell-text-muted` | `#49617a` | `#5c6575` |
| `--ps-shell-rail` | `#f4f8fd` | `#f6f7f9` |
| `--ps-shell-accent-soft` | `rgb(11 99 229 / 8%)` | `rgb(47 111 224 / 9%)` |
| `--ps-shell-shadow` | `0 12px 30px rgb(6 26 58 / 8%)` | `0 10px 26px rgb(23 33 58 / 7%)` |

Those six paint the header rule, the destination and room-title ink, the search
field's fill, border, text and icon, the switcher pill and list, the account
trigger and menu, the Menu button, the More sheet and the phone bar's ground,
rule and idle labels. "One quiet, consistent global header" cannot be true
while a route repaints it, so the six are pinned in **shell scope only**, to
the values the shell already resolved on every other route. `/experience` keeps
every one of its own page colours; only the chrome on top of it stops drifting.
The rule carries the same `:not([data-theme="dark"])` guard as every other
colour rule in the file, because these are light-theme literals.

`--ps-shell-ground`, `--ps-shell-stage` and `--ps-shell-accent` are
deliberately **not** pinned: no shell rule paints any of them (§11.4), and they
name the *page's* ground and accent — pinning those would assert a ground this
package does not own, on the one route whose ground genuinely differs.

**6. The shell did not actually own its destination ink.** Found while proving
(5). `.global-header .platform-nav__links a { color: var(--ps-shell-text) }` is
(0,2,1), and `style.css` carries
`body[data-theme="modern-blue"] .platform-nav__links a { color: var(--text) }`
at (0,2,2). On every `platform-shell` route the ink was therefore coming from
`style.css`, not from the shell — invisible while the two resolved the same
value, and visible on `/experience`, where they do not. This is architecture
§7.4's structural point applied to the idle state, and the same correction the
active state already carried. Restated at exactly (0,2,2), using `:where()` for
the dark guard so it costs no specificity: it ties the modern-blue rule and
wins on source order, cannot match a dark body at all, and stays **below**
Opportunity Slate v2's (0,3,2) and Interview Studio's (0,5,2) page-scoped
overrides, both of which keep winning. Colour only — no page's type moves.

### 14.5 Recorded for the Colour audit, not fixed here

- **`.peerslate-home-page`'s token block is dead.** It declares `--surface`,
  `--border`, `--text`, `--accent` and more at (0,1,0), and
  `body[data-theme="modern-blue"]` outranks it at (0,1,1) on every page, so its
  values never win anywhere. It is page-owned, in a byte-locked file.
- **The upstream fix for §14.4(5) is not the shell's.** Either `/experience`
  takes the same light context as every other route, or the shell's palette
  stops being page context. Both are the audit's call; the six literals in
  `public-navigation.css` are the one place to reconcile.
- **Interview Studio's sage was never exercised.** Its warm authenticated shell
  is scoped `body.interview-studio-page:has(.is[data-authenticated="true"])`,
  and `data-authenticated` does not appear in any local render, signed in or
  out. Every consistency figure below therefore excludes it. Removing that sage
  is the owner's stated intent for the cross-site audit and is explicitly out of
  this package's scope.
- **The More sheet's current row keeps a leading accent bar the switcher's
  current row does not have.** Both now agree on fill, ink and weight; the
  `::before` pill is an extra marker in one panel only. Left alone as a
  composition question rather than a colour one.
- **The logo's own `drop-shadow(0 1px 1px rgb(6 26 58 / 22%))` stays a
  literal.** It is the artwork's treatment, not a shell surface role, and the
  mark is locked.
- **The new brand divider inherits `--border`'s known weakness.** `#d9e2ec` on
  `#ffffff` is 1.31:1, the same figure §7 already records for the search
  field's boundary. It is a purely decorative separator between a logo and a
  heading that are legible without it, so SC 1.4.11 is not engaged; it moves
  with the border value when the audit sets one.
- **Idle ink differs between the header row and the phone bar** —
  `--ps-shell-text` against `--ps-shell-text-muted`. Kept: both approved boards
  draw the bar's idle slots grey and the desktop destinations dark.
- **`/experience`'s destination row is still laid out differently, and this is
  not a colour problem.** Found by eye while reviewing the frames, then
  measured at 1440 signed out:

  | Route | `justify-content` | column gap | first link | last link ends |
  |---|---|---|---|---|
  | `/`, `/peerslate`, `/interview-studio`, `/petec/resume` | `flex-start` | 15.84px | x = 248 | x = 777 |
  | `/experience` | **`space-evenly`** | **33.12px** | x = 300 | **x = 1046** |

  `cinematic.css` carries `body.cinematic-home-page .platform-nav__links
  { justify-content: space-evenly; gap: clamp(1.15rem, 2.3vw, 3rem) }` at
  (0,2,1), which outranks the shell's (0,2,0) — the same class of defect as
  §14.4(6), in geometry rather than colour, and precisely what ARCHITECTURE §2
  says loading this file last is supposed to prevent. The Editorial Top Bar's
  composition is "left-packed beside the logo rather than space-evenly across
  the row" (§2.2), so `/experience` is not rendering the approved shell.

  **Deliberately not fixed in this round.** The owner's instruction was colour,
  and this is composition: re-packing that row is a plainly visible change to
  the header of the page `base.html` calls the protected cinematic homepage,
  on a route the owner has not looked at in this round. The colour pin above is
  a different case — those deltas are sub-perceptual and were explicitly asked
  for. This wants an owner decision, and it is one line of CSS when it comes.

### 14.6 Verification

Two servers pinned to this worktree, each token-checked against the on-disk
SHA-256 of `public-navigation.css` before any measurement.

**Colour consistency** — `verify_shell_colour_consistency.py`, 8 routes × 2
auth states × 4 viewports, every panel opened, the search field measured at
rest rather than focused:

| Question | Result |
|---|---|
| Does each rendered surface paint the token its declaration names? | **769 of 769 match, 0 mismatch** |
| Does each surface paint one value on every route? | **59 of 59 surface × width combinations, 0 drift** |

**Tokenization** — `verify_tokenization_computed.py`, now including
`/experience`, because a proof that never visits the one route where the family
is not a pure alias would be proving the wrong thing:

| | value |
|---|---|
| states compared | **260** |
| node snapshots | **26,788** |
| deltas on the seven `body.slate-light` routes | **0** |
| deltas on `/experience` | 42,649, **every one** of the six pinned values |
| unexpected deltas | **0** |

**The revision itself** — `verify_css_revision_inert.py 70d9c4e`, custom
properties included, the More sheet opened so its ground and elevation are
visible. This round is not inert by design, so the question changed from "did
anything move?" to "did anything move that I did not intend and cannot name?".
60 states, 6,015 node snapshots, 22,900 deltas:

| Deltas | Intent |
|---|---|
| 6,015 | the new `--ps-shell-shadow` token exists in one variant only |
| 14,422 | the cross-route palette pin, `/experience` only |
| 2,052 | the More sheet's account rows take the shared menu ink |
| 219 | **the logo revealed at every width in every auth state** |
| 90 | the room title's divider, and its 34.01rem–64rem band |
| 36 | the Menu button joins the one control ground |
| 36 | the More sheet joins the one panel elevation |
| 30 | F2 — the switcher's current row takes its persistent fill |
| **0** | **unexplained** |

The same run re-confirms F1: across those 60 states the four bar elements were
observed 60 / 130 / 100 / 100 times and **4,684 watched property comparisons
were identical**, so splitting the parent `.mobile-tabbar` rule moved nothing.

**The Interview byte lock, fourth recapture.** Taken from a normalized clean
tree, per the method §9 and §12.1 describe: everything was committed, the eight
files that feed a `?v=` token were deleted and re-checked-out, and disk bytes
were confirmed byte-equal to the git blob for each before capture
(`public-navigation.css`, `base.html`, `public-mobile-nav.js`,
`public-site-search.js`, `style.css`, `site-search.js`, `mobile-nav.js`,
`interview-studio.css`).

| | Before | After |
|---|---|---|
| `/interview-studio` length | 114833 | **114833 — unchanged** |
| `/interview-studio/history` length | 114610 | **114610 — unchanged** |
| `/interview-studio` sha256 | `081129ef…` | `e5f5d1c3c917eb6bbcaa6cc23719c5186ea619732e90b7e8fb02326143d77448` |
| `/interview-studio/history` sha256 | `095440e4…` | `489bd106f96043c57df5eb6b85e071bf8dacfc6af4dfa488d8026ef09f2bbff0` |

**The lengths did not move, and that is the evidence.** This round's only
template edit is inside a Jinja `{# #}` comment, which never reaches the
response, so the anonymous Interview markup is byte-identical and the sole
delta is the embedded `public-navigation.css` fingerprint. Proven rather than
asserted on both routes: the new token `9b25c57dc7ed` occurs exactly once, and
substituting the pre-round token `4a797a2823ce` back into the normalized
document reproduces the previously locked sha256 exactly, at identical length.

`style.css`, `site-search.js` and `mobile-nav.js` are byte-unchanged
(`2b76a653fdca`, `8fcc302461af`, `1f0687c26f0b`), so §5's `/app` byte lock is
untouched and `tests/test_owner_home.py` still passes.

**Tests.** Focused suites plus both byte locks — `tests.test_navigation`,
`tests.test_auth`, `tests.test_search_visibility`, `tests.test_owner_home`,
`tests.test_interview_studio` and `tests.test_signin_experience`: **401 tests,
OK (1 skipped)**.

Full `unittest discover -s tests -t .`: **3,723 tests, 2 failures and 2
errors**, and all four are this package's known pre-existing set, confirmed by
running those two modules alone — `ScheduledRunnerTests` ×3 in
`test_community_maintenance_off_request_path`, and the owner-only-permissions
check in `test_community_disposable_sql_proof`. None is attributable to this
round.

One extra failure appeared in an earlier full run and did not reproduce:
`test_journal_frontend`'s `test_detail_composition_…` measured a 113.25px title
against an 80px ceiling. Run on its own the module passes 53 of 53. It is a
browser measurement flake under load, and it could not be this round's work in
any case — it drives `/app/journal/moments/…`, and `base.html` does not load
`public-navigation.css` on any `/app*` path.

**Interaction and keyboard**, `verify_shell_interaction.py`: 37 of 38 checks
pass, the same single pre-existing failure as §8 — `/auth/session` returns 503
because a local run has no database. Tab order re-confirmed at 1440: skip link
→ logo → the five destinations → search → account. The room title is a `span`,
so it adds no tab stop and the account menu still returns focus to its trigger.

### 14.7 What this round did not verify

Everything in `INDEPENDENT_REVIEW.md`'s "What none of these rounds verified"
still holds — no hardware, no real tablet path, no live site, no real session,
no screen reader, no non-Chromium browser. Added to it:

- **No independent review.** This round was written and verified by the same
  session.
- **Interview Studio's authenticated warm shell** (§14.5) — never rendered
  locally, so the consistency figures do not cover it.
- **`/the-slate` and `/opportunity-slate` still 404 locally** (§13), so their
  shells were measured on a 404 page carrying the shared shell, not inside the
  room. `/experience`, where the palette pin lands, does return 200 and was
  measured as a real page.
- **Real-device safe-area behaviour** for the phone-bar padding moved by the F1
  split. `env(safe-area-inset-bottom)` resolves to 0 in headless Chromium, so
  the split is proven inert only at inset 0.
