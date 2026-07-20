# Editable component inventory

All components are defined in `source/design_system.mjs` and composed in `source/generate_all.mjs`.

| Component | Variants / role |
|---|---|
| `cinematicAtmosphere` | Separately replaceable independent alpine image plus editable navy/gold vector veils; no member imagery and no board crop |
| `desktopNav`, `navItem` | Home current context; Journal, My Slate, Connections, More dormant |
| `mobileTopBar`, `mobileBottomNav` | Standalone mobile shell; Home/Capture current, future destinations dormant |
| `ownerHero`, `ownerAvatar` | Variable owner identity, private context, generic fixture identity |
| `capturePanel` | Dominant active Capture; standard and visible-focus variants |
| `audienceRail` | My Slate preview, Owner View current context, four dormant preview modes |
| `stageCurrent` | Honest empty Review/Recent plus dormant Resurfaced/Noticed/Connections and current Next |
| `stageFutureMax` | Same geometry with exact nine-object maximum fixture |
| `emptyLiveCard` | Honest category empty variants |
| `dormantCard` | Dark, ivory, and warm polished **Coming later** capability previews |
| `relationshipMaterial` | Abstract content-free relationship surface; no people, counts, messages, or activity |
| `reviewFixtureRow` | Up to three separate generic review fixtures; narrow and long-content layouts |
| `momentFixtureCard` | Recent and Resurfaced test-only record variants |
| `noticedFixtureCard` | Explicit future governed-insight test fixture; never used as current result |
| `connectionFixtureCard` | Explicit no-real-person/relationship fixture |
| `currentNextCard`, `nextFixtureCard` | Quiet current Capture next step and future grounded fixture |
| `boundedRemainder` | One shell-level path after three reviews; no fourth Home record |
| `failureCard` | Partial and complete failure with Retry/safe-return treatment |
| `focusRing` | 3 px marigold focus plus separation edge |
| Evidence composers | loading, partial/complete failure, stale, restricted, recovery, access lifecycle, high contrast, reduced motion, 200% reflow, finite budget, landscape orientation |

## Core palette

- Deep Navy `#071421`
- Elevated Navy `#0D2133`
- Cloud White `#FFFDF8`
- Warm Ivory `#F5F0E7`
- Paper `#FBF8F2`
- Marigold `#D9AA2B`
- Accessible dark-gold text `#8A5A00`
- Focus `#FFD75E`
- Success `#1E725F`
- Error `#A43737`

The generator uses Georgia/Arial fallbacks to keep exported SVG text live and portable. Production typography remains subject to the approved PeerSlate type implementation and font licensing.
