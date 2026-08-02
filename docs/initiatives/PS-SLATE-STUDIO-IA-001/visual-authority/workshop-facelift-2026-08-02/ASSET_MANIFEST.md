# Asset manifest

**Status:** owner-accepted visual facelift, 2026-08-02. This set is the
binding visual authority for two different scopes at once:

1. **Track 1 (this package, implemented now):** the facelift's surface,
   shadow, texture, typography, and action-color tokens apply to the
   **already-live** Workshop screens — My Information / library (`R11`,
   `R12`), Add information (`R13`), Review & save (`R14`), and Saved private
   (`R15`, `R16`). These six files are the direct visual reference for Track
   1's restyle of `static/css/workshop.css`.
2. **W2 authority (later slice, not implemented here):** `R01`–`R10` and
   `R17` are the accepted **Work-on-Something** visual direction (opening/
   returning, focused question, first run, AI-unavailable, AI review, and
   the cross-product voice-input state board). They govern the future W2
   session-opening build gated elsewhere in this initiative (see doc 20 §4)
   and are recorded here now so the full accepted set is hash-pinned in one
   place. Track 1 does not build any W2 screen and does not reference these
   ten files for CSS derivation beyond the shared token system (matte
   surfaces, shadow recipe, texture, navy/royal-blue) that `R09` and `R15`
   both make legible.

All files are sRGB PNG. Hashes are lowercase SHA-256, generated with
`shasum -a 256`.

| File | Dimensions | Scope | Status |
|---|---:|---|---|
| `R01-opening-returning-desktop-facelift.png` | 1536×1024 | W2 (later) | Owner-accepted facelift |
| `R02-opening-returning-mobile-facelift.png` | 724×2172 | W2 (later) | Owner-accepted facelift |
| `R03-focused-question-desktop-facelift.png` | 1536×1024 | W2 (later) | Owner-accepted facelift |
| `R04-focused-question-mobile-facelift.png` | 724×2172 | W2 (later) | Owner-accepted facelift |
| `R05-first-run-desktop-facelift.png` | 1448×1086 | W2 (later) | Owner-accepted facelift |
| `R06-first-run-mobile-facelift.png` | 724×2172 | W2 (later) | Owner-accepted facelift |
| `R07-ai-unavailable-desktop-facelift.png` | 1448×1086 | W2 (later) | Owner-accepted facelift |
| `R08-ai-unavailable-mobile-facelift.png` | 724×2172 | W2 (later) | Owner-accepted facelift |
| `R09-ai-review-desktop-facelift.png` | 1672×941 | W2 (later); token reference for Track 1 | Owner-accepted facelift |
| `R10-ai-review-mobile-facelift.png` | 724×2172 | W2 (later) | Owner-accepted facelift |
| `R11-library-populated-mobile-facelift.png` | 724×2172 | **Track 1 — live screen** | Owner-accepted facelift |
| `R12-library-empty-mobile-facelift.png` | 724×2172 | **Track 1 — live screen (empty state)** | Owner-accepted facelift |
| `R13-add-information-mobile-facelift.png` | 724×2172 | **Track 1 — live screen** | Owner-accepted facelift |
| `R14-review-save-mobile-facelift.png` | 724×2172 | **Track 1 — live screen** | Owner-accepted facelift |
| `R15-saved-private-desktop-facelift.png` | 1448×1086 | **Track 1 — live screen; desktop card-language reference** | Owner-accepted facelift |
| `R16-saved-private-mobile-facelift.png` | 724×2172 | **Track 1 — live screen** | Owner-accepted facelift |
| `R17-voice-input-state-board-facelift.png` | 1536×1024 | W2 (later) | Owner-accepted facelift |

See `SHA256SUMS.txt` for the exact hash of each file, including
`00_READ_ME_FIRST.md`.

## Known gap — desktop library/add/review references

The accepted set has no desktop capture for the library, add, or review
screens; `R11`–`R14` are mobile-only. `R15` (saved/private) and `R09` (AI
review canvas, used for Track 1 only as a token reference — texture, rails,
typography, shadow recipe — never as an AI-review layout instruction) are
the only desktop facelift compositions available. Track 1 therefore applies
the facelift's token system (matte white card surfaces, the soft layered
shadow recipe, the icy concentric-ring/dot canvas texture, navy ink
typography, royal-blue actions) to the **existing desktop compositions**
already implemented for My Information, Add information, and Review & save,
rather than inventing new desktop layouts. This is a documented adaptation,
not a new visual-direction decision — the existing desktop layout,
composition, and information architecture are unchanged; only the token
system (surface/shadow/texture/type/action-color) is applied. If Pete wants
a bespoke desktop composition for these three screens, that returns to the
ChatGPT visual-creation lane as new reference material.

## Authority note

This is a material **visual-direction decision** (owner-accepted, ChatGPT
visual-creation lane per `OWNER_VISUAL_INTEGRITY_STANDARD.md`), not runtime,
architecture, merge, deployment, or live-product evidence. See
`docs/initiatives/PS-SLATE-STUDIO-IA-001/20_ROUND2_VISUAL_ACCEPTANCE_AND_RECONCILIATION.md`
§6f for how this set supersedes the round-3 heavy shadow dial and for the
scroll-cap adaptation record.
