# PS-FEED-003 — Community & Feed round 2 (delivered 2026-07-17)

Owner-directed refinement round on the Living Stream Feed (PS-FEED-001),
the community chrome, the Slate Board page, plus two sizing tweaks
(homepage, résumé). Everything on the Feed remains fixture/demo data;
voice, AI, publishing, uploads, and reminders are simulated in-page and
save nothing.

## Feed (/feed-living-stream)

- **Wider desktop feed**: column 790→860px, shell 1160→1260px, rail
  300→320px; the reminders/Catch-Up rail is now a standing part of the
  desktop feed rather than a special composition.
- **Sticky-note reminder pad** pinned at the top of the right rail:
  yellow pad, dashed rules, add-a-reminder input, and a per-note
  "+ Board" action (simulated) — reminders can also go to the Slate
  Board. Left rail gains a "Your week" pulse card.
- **Polaroid & film-strip frames** — member-chosen options, never
  defaults: a picture can render as a tilted instant photo with a
  handwritten (Caveat) caption; a video renders INSIDE a piece of film
  with sprocket holes above and below. Both available in the composer
  via frame checkboxes on attached media, and shown in the stream by
  two new polaroid mockups and one film mockup.
- **More post mockups**, including fun ones (summit polaroid, demo
  film video, 5k milestone, Saturday coffee polaroid) using existing
  approved sample images.
- **Composer pop-out**: label "Transcript" → "What you said" (no
  "Original transcript"/"original wording" phrasing anywhere); voice
  capture now attaches the recording as a playable audio chip; an
  "Add to this post" row offers Photo / Video / Document / Audio
  (simulated attachments that carry through to the published fixture
  post); "PeerSlate proposal" branding replaced with "Suggested post ·
  editable" (+ "AI-suggested draft" chip — AI output remains a proposal
  the member approves); "Also connect to" targets are now My Story,
  Slate Board, Resume.
- **For You / Following tablist removed** (Following doesn't fit the
  Feed). The tab row is now the community switcher — People &
  Interests · Feed · The Break — which also fixes "once you are in the
  feed there is no way back."
- **"Design preview" badge removed**; one quiet truthfulness line
  remains: "Sample data — nothing on this page is saved or shared."
- Fixed a latent bug: `.respond-tray` had `display:flex` beating the
  `hidden` attribute, so every post showed the tray expanded.

## Community chrome

- The Break is back as a community option (tab on People & Interests
  and in the Feed switcher → /the-slate/break).
- The "News Feed · soon" placeholder chip retired (a real Feed tab now
  exists); "Feed Preview · preview" chip renamed to just "Feed".
- The floating Ask Pete AI launcher is hidden on every the-slate-page
  (community is about members, not Pete's profile assistant).

## Feed ⇄ The Break: one ecosystem (owner feedback, same day)

- The Break was rebuilt INSIDE the community shell: the same left
  sidebar as the Feed (Capture, Journal, Feed, The Break, Board, Work,
  Studio, "Your week", Settings/user — now shared partials
  `community_sidebar.html` / `community_mobile_nav.html` /
  `community_icons.html`), the same page head, and a prominent
  segmented **Feed ⇄ The Break** switcher (`community_switch.html`)
  top-right on both views. Capture on The Break deep-links into the
  Feed's voice state.
- Removed from The Break: the old Slate-hub head strip and the
  People & Progress / Pulse layer bar. Removed from the Feed switcher:
  People & Interests (for now — the page itself still exists at
  /the-slate). The Break joined the sidebar and the mobile bottom bar
  (replacing the inert "More").
- Dark theme: the community app sheet deliberately stays light, so the
  Break embed re-asserts the light card/body tokens inside `#feed-app`
  (the site-wide dark pass was painting dark cards with flipped type
  onto the white sheet).

## Slate Board page

- My Slate and Daily Slate are combined onto /slate-board, stacked
  below the whiteboard (anchors #my-slate, #daily-slate). Their content
  now lives in shared partials (partials/my_slate_section.html,
  partials/daily_slate_section.html) rendered by both the board page
  and the still-working standalone routes. No duplicate element IDs;
  the-slate.js loads alongside slate-board.js. The People & Interests
  rail links point at the new anchors.

## Sizing

- Homepage (home-v3): container 82.5→90rem, hero grid rebalanced
  (copy 1fr / stage 1.24fr / destinations 0.92fr), lede measure 33rem.
- Résumé: 10% smaller on desktop via `zoom: 0.9` on `.resume-v2`
  children (children only, so the fixed full-bleed backdrop pseudo
  keeps covering the viewport).

## Tests

- `tests/test_feed_prototype.py` and
  `tests/test_people_interests_feed.py` updated to assert the new
  intended state (community switcher, sample-data line, no Following,
  no News Feed chip). Full suite: **221 tests OK**.

## Checklist (docs/INITIATIVE_CHECKLIST.md)

Canonical objects: none (fixture-only surfaces). Owner/audience:
unchanged; composer privacy defaults unchanged (private option intact,
publishing stays an explicit member decision). AI vs deterministic:
unchanged — AI output is still a proposal ("Suggested post"), never an
automatic edit. Provenance: sample data labeled. Accessibility: the
switcher is a labeled nav of real links; overlay focus trap unchanged;
reminder pad is a labeled form; frames are checkbox options. Tests:
221 green. Truthfulness: preview badge removed but the sample-data
disclosure stays; all simulated actions announce themselves as
simulated. Language: no banned filler introduced.
