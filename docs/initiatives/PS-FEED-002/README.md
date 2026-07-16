# PS-FEED-002 — Community Feed and Respond (public-safe slice, 2026-07-16)

## What landed
- **Right rail removed** from the People & Interests board: pick-me-up
  quote, goal check-in, weekend challenge (with fabricated join count),
  community poll, and share-good cards deleted per rules 26/33; the board
  recenters into the freed width. The rail returns as the single private
  Note card with PS-JOURNAL-002 (owner-held). Fixture rail data pruned so
  nothing can silently resurrect the modules.
- **Respond system** (rule 28): the shared reaction vocabulary is now
  Celebrate / Support / I relate / Ask / Offer help — defined once in
  services/people_interests_feed.py, validated server-side, embedded for
  the client; goal posts emphasize Offer help instead of a separate
  "I'm in" vocabulary. Fixture reaction counts migrated
  (applaud→celebrate, inspired→i relate, rooting→support, im_in→offer help).
- **Feed design preview**: the single Encourage action becomes a
  `Respond` control opening a compact intention tray (idempotent,
  aria-pressed, change/remove supported, no public leaderboards);
  comment-level Encourage → Support; "Original transcript" → "Transcript".
- **No Ask Pete AI inside Community** (rule 30): the header launcher,
  floating toggle, chat panel, and sub-header Ask button are not rendered
  in pine rooms (/the-slate*, /feed-living-stream*); they remain
  everywhere else.

## Deferred to the auth phase (reported, not mocked)
Real comments/replies/mentions/moderation, per-member response state,
the wider three-column Feed with the Note card, and the composer's
journal connections all require sign-in and owner records. The corkboard
keeps its honest per-browser preview persistence.

## Verification
Full suite **208 tests OK** (updated reaction tests + 3 new rule tests:
banned modules absent, Respond vocabulary live, no Ask AI in Community).
Browser: /the-slate renders recentered board, pine accents, no rail, no
Ask AI; Feed preview Respond tray verified. Checklist: no canonical
records (fixtures); server validates the vocabulary; nothing mocked as
persistent.
