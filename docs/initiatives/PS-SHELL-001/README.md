# PS-SHELL-001 — Site Shell: width, headers, ground, and type

**Status:** Planned — set up 2026-07-21 per Pete; starts after the Journal J1
release wave. **Owner direction source:** Pete's 12-thought review
(2026-07-21) + his three example images (filed in the transcript; formal
visual authority to be accepted before implementation per the pixel rule).

## Scope (Pete's items 6, 8, 9, 10, 11, 12)

1. **One consistent content width** across every page (~1120–1200px stage per
   the owner's examples), with the Context Rail proportions from
   `OWNER_CONTEXT_RAIL_STANDARD.md`.
2. **One consistent header** everywhere: primary nav (Pete's Slate ·
   Community · Interview Studio) + slim contextual sub-nav, signed-in state
   with avatar + Sign out (the interim global Sign out shipped 2026-07-21,
   PR 144; this package integrates it properly).
3. **Two-tone ground:** one tone outside (frame), one inside (stage),
   inverted between light and dark themes. The Journal's desk-and-page
   pattern is the reference feel.
4. **Room flavor watermarks:** subtle low-contrast silhouettes per room
   (owner example: a singer + mic beneath the Interview Studio layer; book
   motif for Journal; corkboard hints for Community). Quiet, never busy.
5. **Type scale review:** current sizes run small; study 2–3 candidate
   scales on real pages (owner examples show ~17–19px body with large
   display headers), Pete picks, roll out with the width work.

## Rules
- The **pixel rule** applies: accepted mockups' sampled pixels are the
  authority; no substitution with legacy tokens.
- Fable constructs · Sonnet (xhigh) implements · Opus (xhigh) reviews with
  the identical bar + kickback loop · Pete visually accepts.
- Site-wide color *scheme* decisions remain Pete's separate conversation;
  this package implements structure + the two-tone pattern he described.
- One writer, one branch; no route changes (navigation belongs to the
  deferred route-map package).

## Entry gate
Journal J1 accepted and released; visual authority for the shell accepted by
Pete; no overlap with any active lane's files.
