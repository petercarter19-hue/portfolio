# PS-THEME-002 — Layered Ink & Signal Gold dark theme (delivered 2026-07-17)

Supersedes the visual system of PS-THEME-001 ("Monochrome & Signal
Gold"), which kept warm-paper pages under an ink header and therefore
read as a light theme with dark chrome. Owner direction (2026-07-16):
replace it with a real dark theme — "black layered with white layered
with black … and gold when needed."

## The layer system

True dark, never pure black; elevation is expressed by lightening each
layer (the standard dark-UI pattern used by Material's dark elevation
guidance and dark-first products such as Linear/Vercel):

| Layer  | Hex       | Used for                                   |
|--------|-----------|--------------------------------------------|
| well   | `#060708` | footer, insets, the Interview Studio stage backdrop family |
| page   | `#0E0F12` | the canvas behind everything               |
| card   | `#17191E` | cards, rails, panels                       |
| raised | `#1E2127` | nested cards, hover, popovers, ghost buttons |
| hairline | `#262A31` (`#1D2026` soft) | borders on every dark layer |

Type on dark: `#F4F3EF` primary, `#C6C4BC` secondary, `#A5A399` muted
(≥4.5:1 on the card layer). Gold: `#D8A928` for buttons — always with
ink `#0B0C0E` text — and `#E3B83A` as text-safe gold on any dark layer
(≈9:1 on ink); `#8A6500` remains only for text on the paper pop layer.

**The paper pop layer** (`#F6F5F0`) is the "white layered between
blacks": the résumé document renders as solid paper slabs floating on
the black stage (its ink-on-paper internals from PS-THEME-001 are kept
verbatim), the Slate Board whiteboard stays a bright white board hung
on a black wall, the story chapters stay white slabs over the dark act
stages, and the marketing preview card keeps a white metrics strip.
The Living Stream feed keeps its coherent white app sheet (the
prototype hardcodes white surfaces + navy type throughout).

## What changed (all scoped under `body[data-theme="dark"]`)

- `static/css/style.css` — every dark token block remapped (shared
  Modern-Blue-era vars, Iris `--ps-*`, Foundation-C tokens, slate-light
  re-assert, my-story/work remap, `--home-*` marketing palette); dark
  sub-header strip, dark mobile tab bar, footer as the well layer,
  ink-offset gold focus ring, gold sub-header Ask-AI chip, marketing
  hero wash/ghost/chip/metrics fixes, `.ps-btn--primary` pinned to
  gold-with-ink-text.
- `static/css/sky-glass.css` — site-wide sky becomes the black canvas
  with a whisper of gold atmosphere; glass tokens become planted dark
  cards; profile band/tab strips become graphite layers.
- `static/css/editorial-glass.css` — the planted-card system flips to
  dark cards (`--ps-card-*` and the grouped selector sweep); the
  résumé/ledger/story fixed backdrops paint the shared black stage;
  skills constellation labels lifted to off-white.
- `static/css/resume2.css` — page canvas dark (fixed `::before`
  becomes the stage, `::after` wash disabled); section slabs solid
  paper; document internals untouched.
- `static/css/living-resume-v2.css` — résumé sub-header strip graphite
  with gold active tab; `--lr-*` intentionally stays paper-side for
  the slab internals.
- `static/css/slate-board.css` — dark wall + dark controls rail (light
  labels, gold active tool, ink text pinned on white mini-pills and
  on-canvas controls), donut/legend graphite segment flipped to
  off-white; whiteboard canvas and sticky notes untouched.
- `static/css/interview-studio.css` — dark rail/cards on the black
  canvas with the workspace as the deepest black stage; hero H1,
  persona chip, mode cards, filters, and history selects pinned to
  off-white (ink-950 stays true ink for white inputs/gold buttons).
- `static/css/people-interests.css`, `skills-cinematic.css`,
  `story-acts.css`, `feed-living-stream.css`, `homepage-scenes.css` —
  accents lifted from gold-ink to dark-safe bright gold; canvas-level
  type flipped to off-white; user content (corkboard, notes, photos,
  avatars) untouched. Fixed a PS-THEME-001 bug: the skills page dark
  pass targeted `.skf` but the container class is `.skills-film`, so
  its ink vars never flipped (the "Skills in" headline stayed navy).
- `docs/PEERSLATE_SITE_RULES.md` — rule 78a rewritten to record the
  new system.

## Decisions

- The light/default theme remains byte-for-byte behavior-identical —
  every rule stays scoped under `body[data-theme="dark"]`; the toggle,
  storage key, and anti-flash script are unchanged from PS-THEME-001.
- Paper pop layers are deliberate composition, not leftovers: the
  résumé is a paper document on black felt; the whiteboard is a white
  board on a black wall. This is the owner's "black layered with white"
  direction made literal.
- Semantic colors survive in dark: green = verified/strength (lifted
  to `#5ABF95`/`#69AE92` for contrast), amber = improvement, red =
  destructive/recording only.
- `--ps-ink-950` deliberately stays true ink in dark: it is the text
  color on white inputs and on gold buttons, both of which keep light
  surfaces. Anything on a dark layer that used it is pinned off-white
  explicitly.

## Verification

- Full suite: **221 tests OK** (`python -m unittest discover -s tests`).
- Browser (dev server, dark toggled per page): homepage, /peerslate
  marketing, Living Résumé, My Story, Slate Board, Interview Studio
  (desktop + mobile layout), Community People & Interests, Daily Slate,
  Skills, About, Contact, Explore Profiles, Career Search, My Network,
  Hobbies. A computed-style contrast audit (text vs effective opaque
  background) ran on each page; remaining flags were confirmed false
  positives (white text over photos/gradients).
- Light theme spot-checked after the change: renders identically with
  the switch off.

## Checklist (docs/INITIATIVE_CHECKLIST.md)

Canonical objects: none touched (presentation only). Owner/audience:
unchanged. Private/public: unchanged. AI vs deterministic: unchanged
(theme choice is client-side preference state). Provenance: n/a.
Accessibility: muted text ≥4.5:1 on the card layer, gold text pairs
(#E3B83A on ink ≈9:1), gold buttons carry ink text, gold focus ring
with ink offset visible on every layer, reduced-motion behavior
unchanged. Tests: 221 green. Export/delete: n/a. Truthfulness: the
toggle does exactly what it shows; no mocked controls. Language rules:
no new user-facing labels.
