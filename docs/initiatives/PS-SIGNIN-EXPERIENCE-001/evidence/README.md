# PS-SIGNIN-EXPERIENCE-001 — visual evidence

All captures are headless Chromium (Playwright) against a local build of this
branch. The interactive browser pane cannot composite screenshots in this
environment, which is why every image here comes from a script.

"BEFORE" images are the same route, viewport, and state rendered by a build of
`origin/main` at the package base commit
`388f47307a65bec6e70731a1b7794acad2dd1884`, extracted with `git archive` and
run on its own port, so the pairs are a real comparison rather than a
recollection.

## How the states were produced

Both waking states are genuine `DatabaseServiceError` renders, not mock-ups:
the preview process was started with an intentionally invalid
`AZURE_SQL_CONNECTIONSTRING`, so `db.get_connection()` rejects it immediately
and the route takes exactly the branch a paused Azure SQL serverless database
takes. No secret value was read, printed, or committed.

| State | How |
|---|---|
| Owner Home waking (`/app`, flag on) | dev identity on, invalid connection string |
| Identity storage waking (`/app`) | Easy Auth principal header, dev identity off, invalid connection string |
| Owner Home contract failure | `OwnerHomeContractError` cannot be produced from a preview without a malformed payload, so the same Flask app rendered that branch and the exact bytes were served to the browser |
| Signed-in header | dev identity on |
| Signed-out header | dev identity off, no principal header |

## Item 2 — graceful database wake

| File | What it shows |
|---|---|
| `item2-ownerhome-BEFORE-desktop-1440.png` | The problem: a paused database presented as "HOME DATA FAILED / Owner Home data could not load" |
| `item2-ownerhome-waking-desktop-1440.png` | The same failure now reads as a transient wake-up, in the same panel |
| `item2-ownerhome-waking-mobile-390.png`, `-320.png` | Mobile |
| `item2-ownerhome-waking-zoom200-720.png` | 200% zoom (1440 logical / 720 CSS px) |
| `item2-ownerhome-waking-desktop-1440-reduced-motion.png` | `prefers-reduced-motion: reduce` — computed `animation-name` is `none` |
| `item2-ownerhome-waking-focus-stop-control.png` | Visible keyboard focus on "Stop checking automatically" |
| `item2-ownerhome-waking-stopped.png` | After stopping: the control is gone and the status line says so |
| `item2-ownerhome-contract-failure-unchanged-1440.png` | `OwnerHomeContractError` still renders the released failure card, unchanged |
| `item2-identity-BEFORE-desktop-1440.png` | The identity waking page before: honest copy, manual retry only |
| `item2-identity-waking-desktop-1440-{light,dark}.png` | After, both themes |
| `item2-identity-waking-mobile-{390,320}-{light,dark}.png` | Mobile, both themes |
| `item2-identity-waking-zoom200-720-{light,dark}.png` | 200% zoom |
| `item2-identity-waking-desktop-1440-reduced-motion.png` | Reduced motion |
| `item2-identity-waking-focus-stop-control.png`, `item2-identity-waking-stopped.png` | Focus and stopped states |

## Item 5 — signed-in mobile header overlap

`item5-header-BEFORE-signed-in-{320,360,390,414}-light.png` are the base build.
At 360/390 the theme toggle and the Menu button draw on top of the wordmark; at
320 and 414 the Menu button or the toggle does.

`item5-header-signed-in-{320,360,390,414}-{light,dark}.png` and
`item5-header-signed-out-{320,360,390,414}-{light,dark}.png` are this branch.
Measured across all 32 route/width/theme/auth combinations, no two header
controls overlap and no page scrolls horizontally.

`item5-header-desktop-1440-{light,dark}.png` is the desktop header. It is
pixel-identical to the base build; so are 1280, 1100, 1025, 900, 744, 640 and
545px, on both `/` (platform shell) and `/petec` (portfolio shell), light and
dark — 32 pixel comparisons, all zero differing pixels. The change only takes
effect below 34rem (544px).
