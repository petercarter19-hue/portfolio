# PS-BRAND-NAV-002 — Deep Navy Gold light theme (delivered 2026-07-17)

Replaces the Iris Foundry (purple/plum) light-theme system with **Deep
Navy Gold**, the navy direction from the PeerSlate Color Direction Study
(`Design ideas/PeerSlate-Color-Study-Package/`, direction slug
`deep-navy-gold`). Owner direction: "implement the navy blue theme
instead of the Iris theme … follow that navy blue theme from the folder."

The dark theme (PS-THEME-002, deployed) is **unchanged** — the owner
explicitly asked to leave it as-is. Every change here is light-theme only.

## The system

From the study's Deep Navy Gold palette ("Cloud white + ink navy +
marigold"), one authoritative navy + marigold applied consistently across
every room, rather than six competing room hues:

| Token | Value | Role |
|-------|-------|------|
| canvas | `#F6F7FA` | cool cloud-white page |
| surface | `#FFFFFF` | cards |
| ink | `#141A28` | body / heading text (deep navy) |
| muted | `#5B6472` | secondary text (5.6:1 on canvas) |
| border | `#DDE2EB` | cool neutral hairlines |
| primary | `#203767` (strong `#132447`) | primary actions, headings, active/selected |
| primary-soft | `#E7ECF4` | selected/soft navy fills |
| marigold | `#B87900` (text-safe `#8A5A00`, soft `#F4E4B4`) | evidence chips, progress, gold highlights |
| success | `#1E725F` | success only |

Contrast (study checks): ink-on-canvas 16.2:1, white-on-primary 11.6:1,
primary-on-accent-soft 9.2:1 — all comfortably AA/AAA.

## What changed (light theme only)

- **`style.css`** — the `:root` Iris Foundry block became Deep Navy Gold;
  all six `body[data-room=...]` blocks now point `--ps-page-accent` at the
  one navy (Board and Résumé keep a marigold-soft highlight fill for their
  evidence/goal chips). Foundation-C tokens `--ps-product-indigo` /
  `--ps-ai-cyan` / `--ps-evidence-amber` remapped to navy/marigold.
  Profile-tab active states and the overview AI ask-bar (was teal) → navy.
- **Per-page palettes** brought onto navy + marigold: `resume2.css`
  (`--r2-indigo/azure/cyan` → navy, `--r2-amber` → marigold),
  `living-resume-v2.css` (`--lr-*`), `feed-living-stream.css`
  (`--indigo/azure/cyan/amber` + hardcoded active states + the voice
  listening-ring), plus periwinkle/teal sweeps in `interview-studio.css`,
  `slate-board.css`, `story-acts.css`, `people-interests.css`,
  `owner-app.css`, `sky-glass.css`.
- **`homepage-scenes.css`** — `--hv-indigo` family → navy, purple halos →
  navy, warm-ivory background → cool cloud-white. Decorative scene accents
  (azure/cyan/green destination icons) kept for a little life.
- **Community note tags** (`.pi-tag--idea`, `.pi-tag--quote`,
  `.pi-chip--violet`) — violet → navy.
- **Preserved as user content** (never recolored): member avatar and pin
  identity gradients (`.pi-ava--*`, `.pi-pin--*`, feed `.av-*`), Slate
  Board sticky-note colours, member photography.

## Decisions

- **Unified, not per-room.** The study presents Deep Navy Gold as a single
  cohesive palette, and its résumé + interview mockups use identical navy +
  marigold with no room-hue variation. The `data-room` plumbing stays
  (components still read `--ps-page-accent`) but every room resolves to
  navy — the cleanest, most faithful reading of the mockups.
- **Marigold, not bronze.** The old champagne bronze `#B87422` becomes the
  study's marigold `#B87900`; text-safe `#8A5A00` for small gold text.
- **Dark theme untouched** — owner decision. Verified no regression:
  `body[data-theme="dark"]` re-declares its own tokens, so the light
  `:root` swap does not leak into dark. Spot-checked homepage + résumé in
  dark after the change; identical to the deployed dark theme.

## Verification

- Browser (light): homepage, Living Résumé, Interview Studio, My Story,
  Slate Board, Community People & Interests, Feed — all navy + marigold,
  matching the study mockups. A purple/periwinkle hue-detector (hue
  248–320, sat >0.28) ran per page; the only hits (violet note tags) were
  fixed and re-scanned clean.
- Browser (dark): homepage + résumé confirmed unchanged.
- Full suite: **233 tests OK** (`python -m unittest discover -s tests`).

## Reference

Study package (local, git-ignored): `Design ideas/
PeerSlate-Color-Study-Package/` — mockups `mockups/*_deep-navy-gold.png`,
tokens `tokens/peerslate-color-directions.json` (slug `deep-navy-gold`).
