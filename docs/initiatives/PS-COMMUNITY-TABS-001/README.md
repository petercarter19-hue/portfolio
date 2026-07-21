# PS-COMMUNITY-TABS-001 — Community: remove People & Interests, adopt the Studio tab model

**Status:** Planned — set up 2026-07-21 per Pete; may start after the Journal
J1 release wave. **Owner direction source:** Pete's 12-thought review
(2026-07-21, items 1–2) + his Feed example image.

## Owner direction
- **Remove the People & Interests board** from Community (it overlaps Feed
  almost completely).
- **Adopt the Interview Studio tab pattern** — the seamless Interview Me /
  AI / Video / History model — as Community's structure: **Feed · The Break ·
  Saved** (final tab set confirmed with Pete at kickoff; P&I's "Saved notes"
  value folds into Saved).
- The owner's Feed example image (wide stage, composer, Reminders note,
  Catch Up card, Feed ⇄ Break toggle) is the directional target; formal
  visual authority accepted before implementation per the pixel rule.

## Boundaries
- **Internal restructure only:** existing `/the-slate/*` URLs keep working
  (redirects to the surviving views); no new top-level routes — the full
  navigation cleanup remains the deferred route-map package.
- Honest sample-data labeling stays (the shipped sample-community note
  pattern).
- All community write endpoints and privacy rules unchanged.
- Fable constructs · Sonnet (xhigh) implements · Opus (xhigh) reviews
  (identical bar) · Pete visually accepts before merge.

## Landing decision (owner, 2026-07-21)
**Confirmed: Feed is Community's landing view**, with the seamless
Studio-style transition to **The Break** on click — the same no-reload-feel
tab pattern as Interview Studio's Interview Me / AI / Video / History. The
package is kickoff-ready once the Journal J1 wave completes and its visual
authority is accepted.
