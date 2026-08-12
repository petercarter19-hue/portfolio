# Measured targets from the locked mockups (region-based, lock 01 @1672x941)

## Colors
| Element | Measured | Note |
|---|---|---|
| Page canvas | #fdf9f6 | warm white-ivory; header identical |
| Rail background | #fcf7f3 | one step warmer than canvas; FLAT (no card/shadow) |
| Answer card fill | #fdf9f6 | same family as canvas — differentiated by hairline border + soft shadow, NOT fill contrast |
| Question serif ink | #061e47 | deep ink navy (Newsreader) |
| Answer/body ink | #222f5c | softer navy for body text |
| Eyebrow gold (CURRENT QUESTION) | ~#b28a4e cluster (glyph core likely ~#a5762f) | small caps, letterspaced |
| Gold rule under listening line | #c5a264 | thin hairline |
| Active rail pill + primary button | #114427 | DEEP forest — NOT the live page's #1f6248 |

## Geometry (lock 01)
- Rail inner content spans x 38-315 (~277px at 1672 canvas ≈ 16.6% width).
- Primary button: 337 x 82 px (x 432-769, y 777-859) — generous, check icon + label, sits LEFT in the single action band.
- Composition: question text sits DIRECTLY on canvas (no wrapping panel); only the answer is a card; one action band below the card carries [green primary][QUESTION group][COACHING group] with dividers; truth line with lock icon beneath.

## Confirmed systemic build defects (first-batch review)
1. Primary button gold instead of #114427 green, wrong side, arrow icon instead of check.
2. Everything wrapped in one big floating white panel; mockup renders on canvas.
3. Rail is a floating shadowed card; mockup rail is flat with warmer tint.
4. Foreign elements: chips row, DRAFTING/REVIEW READY pill+strip, YOUR ANSWER label, Saving bar, double borders/focus ring nesting.
5. Missing: gold CURRENT QUESTION eyebrow, listening-for line + gold rule composition, Dictate inside card.
6. Craft: ghosted logo (CSS bleed into global header — investigate scoping), struck-through Draft chip, lowercase "general practice", improvement textarea clipping + resize handle, dictation paragraph too prominent.
7. State truth: "Review Revised Answer" reads enabled while "3 remaining" confirmations unresolved.
8. Green token family: build inherited #1f6248/#164934; mockup system is #114427-anchored.

## Cross-lock palette sweep (region modes; AI-generated locks vary slightly per image)
- Primary/action greens cluster: #114427 / #125130 / #17462c / #0f5737 / #0d4e29 → system anchor ≈ deep forest **#114a2b** (hover/strong ≈ #0d3f24). NOT #1f6248.
- Video frame dark fill: **#152640** (deep ink navy, not black).
- Table/panel fills: #fefbf9 / #faf9f5 — same warm-white family as canvas.
- Selected source-card border (07): sage **#b2c1b8**.
- Destructive red: mockup red reads strong (sample #fe0000 raw on 12) but owner
  decision says "muted red"; refine per-element glyph sampling during rebuild —
  candidate band #b0392f–#c03a35; never pure #f00.
- 04b "Developing" gold + 10 chip details: re-sample with tighter boxes during
  those states' rebuild.

## Method note
Region sampling: fills = mode color of region; text = median of darkest cluster.
Refine per-lock during the rebuild; repeat the same measurements on MY captures
and require convergence before showing Pete.
