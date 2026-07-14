# PS-FEAT-002 — People & Interests Living Board

Status: In Progress (parallel review build, 2026-07-13)
Route: `/the-slate/people-interests`
Primary references: Pete's two approved mockups (board + expanded post detail), `PeerSlate_Design_Bible_v0.3.md` §11 (Slate Feed system).

## What this is

A continuous, corkboard-style social feed ("the living board") where posts
render as paper objects — sticky notes, torn scraps, lined notepad sheets,
kraft cards, quote fragments, and polaroid photos. Clicking any object opens
an expanded detail overlay: the post keeps its paper identity on the left,
comments live in their own scrolling column on the right.

Approved decisions captured from Pete's direction:

- **Keep the existing site chrome.** The global header (logo, search, Ask AI,
  Sign In) and the profile sub-header (Overview / My Story / Evidence /
  Projects / Slate Board / Resume) stay exactly as they are. The mockup's own
  two-level header was NOT rebuilt.
- **The three feeds** (Break Feed / People & Interests / News Feed) live in a
  slim contextual strip at the top of the board, using the existing `sf-tabs`
  pattern. News Feed has no page yet and renders as a "soon" chip.
- **No category filter row** (All / People / Goals / …) above the board — 
  intentionally removed to give the board more space.
- **The right rail carries the Break/Pulse spirit** (Pete, 2026-07-13):
  Today's pick-me-up (rotating positive affirmations), a "How's your goal
  coming?" check-in that opens the composer, and the Weekend Challenge with
  its "I'm in" toggle. The standalone Break and Pulse pages are slated for
  retirement; their concepts live on here. The earlier Trending/Recent
  wins/Circles modules were scratched.
- **Papers are hand-placed, not gridded-perfect**: every item stores small
  x/y offsets, varied rotations, mixed paper colors (yellow, green, blue,
  pink, cream, peach, aqua, kraft, violet), attachment styles, and an
  optional emoji flourish doodle. All stored, all deterministic.
- **The detail overlay is centered** — near-card anchoring was tried and
  scrapped because it pushed the shell off screen.
- **The board scrolls continuously** like a feed (cursor pagination +
  IntersectionObserver, 16 items per page), not a single fixed viewport.
- **Post type → paper type.** Each content type maps to a paper treatment,
  and the presentation variant (layout size, paper, color, rotation,
  attachment) is STORED with the item — deterministic, never re-randomized
  on refresh.

## What is implemented

- Page route `the_slate_people_interests` (parallel — nothing existing was
  replaced or modified except registering the new blueprint in `app.py`).
- `services/people_interests_feed.py` — the single storage seam: fixture
  posts + an in-process overlay for posts/comments/reactions/saves.
- `people_interests_api.py` — `/api/feed/*` endpoints: cursor-paginated
  feed, post detail, create post (200-char max), comments (300 max),
  idempotent positive-only reactions, save toggle. Same-origin write
  protections and server-side identity, identical to `peerslate_api.py`.
  The browser never supplies `user_key`.
- `static/js/people-interests.js` — data-driven renderer
  (content_type → paper builder), infinite scroll with paper skeletons,
  expanding composer with counter/validation/optimistic insert, detail
  overlay with focus trap / Escape / backdrop close / focus restore,
  reaction bar from ONE shared config (`REACTION_TYPES` in the service),
  comment composer.
- `static/css/people-interests.css` — cork surface (pure CSS + SVG grain),
  paper families, pins/tape/clips, 4-column dense grid with stored size
  variants, responsive (3/2/1 columns), reduced-motion and forced-colors
  support, mobile bottom-sheet detail view.
- Tests: `tests/test_people_interests_feed.py` (24 tests — routes, API
  contract, protections, pagination stability, fixture vocabulary).

## What is fixture/demo only

- All non-Pete authors are representative sample members (pre-launch
  convention shared with The Slate hub). Pete's posts reuse his real Slate
  Board content and his real photos; sample members only ever get scenery
  images.
- Writes need a signed-in identity. Production has no sign-in yet, so the
  browser falls back to per-browser storage, clearly labeled
  "This browser only" — the same honest convention as the Daily Slate
  composer. Locally (with `PEERSLATE_ALLOW_DEV_IDENTITY=true`) the full
  server path runs end to end.
- The in-process overlay is per-worker and resets on restart. It exists to
  demonstrate the full loop, not to imply durable multi-user storage.

## What requires backend/schema work (proposed, NOT applied)

- `SQL FIles/Migrations/proposed/PS-PLAT-008_people_interests_feed.sql`
  (+ rollback) — feed_posts / feed_post_comments / feed_post_reactions /
  feed_post_saves and their stored procedures. Each field is justified in
  the file header. **Waiting for Pete's approval; nothing was run.**
- **Media uploads:** no upload pipeline exists in the repo today. The
  composer's Photo option is present but honestly labeled "arrives with
  PeerSlate accounts." The intended design: browser → Flask endpoint →
  Azure Blob Storage container (private, SAS-scoped), storing only the blob
  URL + alt text in `feed_posts.media_asset_url` / `media_alt_text`. Never
  base64 in SQL. Requires: a storage account/container, a size/type
  validation layer, and thumbnail generation for board previews.

## Intentionally deferred

- News Feed page (nav chip is present, marked "soon").
- Virtualization of very long boards (revisit after real usage).
- Deep-linking a post via URL hash (Share copies `#post-id` today; the
  overlay does not touch browser history, so Back is never broken).
