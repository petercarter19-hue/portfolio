# Slice OS-4 evidence — the save lifecycle

Captured 2026-08-04 on `work/2026-08-04-opportunity-slate-os4`.
**Every `member-*` frame was RE-CAPTURED 2026-08-04** after the independent
review; see "What the review changed in this set" at the end.

**Every frame here is the SIGNED-IN member.** Saving is signed-in only by
construction (handoff §18): an anonymous visitor has no account for a saved
slate to live in, so a public-mode capture could not evidence this slice at
all. The public side is evidenced by its absence — the preview renders no save
control and says so in words, which is asserted in
`tests/test_opportunity_slate_ai.py`.

**And the site shell around them is the signed-in one.** The first capture
patched only the room's identity, so `base.html` fell through to
`get_optional_principal()` and drew the signed-out header — a Sign In button
no signed-in member ever sees — on every frame claiming to evidence the
signed-in experience (independent review, finding F8). Both are patched now:
each frame carries `data-ps-auth-state="authenticated"`, renders My Slate and
Sign out, and hides Sign In. Asserted in the capture harness itself, so a
future frame cannot silently regress to the wrong shell.

## What is real in these renders, and what is not

- **Real:** every Jinja template, the real `opportunity-slate.css` and room
  script, the real Flask app, the real alignment prompt contract and its
  validators, the real coverage derivation on both the write and the read
  path, slice OS-4's own `compute_input_fingerprint` and
  `_resolve_saved_state`, and the real saved-slate view models.
- **Stood in:** the Anthropic client (a scripted stand-in whose citations are
  verbatim spans of exactly the text it was given — no network call is made,
  and a rewrite would be refused by the real validators), and the database
  row → view mapping. The SQL path has its own proof: the isolated
  apply/upgrade/exercise/rollback/re-apply gate recorded in
  `../../../../artifacts/2026-08-04-os4/sql-gate/` and in the migration's own
  header.
- **Fictional:** the member and their Workshop library. No real member's
  evidence appears in this set.

## The authority split, which is what these sheets exist to show

Image 04 is the package's exact geometry authority. **Image 05 is authority
for saved-state content and actions only** — its flatter cards, compressed
spacing and blue-heavy palette are prohibited (README locked rules, §14-M2).
So the saved and unsaved workbenches here are **one component with a state
prop**: measured at 1440, both render a workbench of 844px, 58.6% of the
frame, with rails at 235/211 — identical, because the geometry is shared and
only the banner, the session chip and the footer actions differ.

## Comparison sheets (authority left, build right)

| File | Shows |
|---|---|
| `compare-09-alignment-saved.png` | Saved state against image 05. Content and actions match: the green `Saved privately` card, the `Current for these inputs` chip, image 05's retention sentence, the filter row in image 05's position, `View saved details` + `Done for now`. Image 05's stacked summary cards and its merged Responsibilities/Informational card are deliberately NOT reproduced — the first is its prohibited geometry, the second is prohibited by §14-M14 |
| `compare-10-alignment-saved-vs-geometry-authority.png` | The same saved build against image 04, which is the geometry it actually follows |
| `compare-11-alignment-stale.png` | `SAVED_STALE` against image 09-c: the same green card with the amber `Inputs changed · Reanalysis required` chip, both of image 09-c's sentences word for word, and Reanalyze / View saved result / Review inputs |
| `compare-12-delete-failed.png` | The delete failure against image 09-d, with the saved slate still fully on screen underneath it |
| `compare-13-alignment-saved-phone.png` | 390 against the desktop authority. There is no mobile lock (§14-M9), so the question these answer is whether it reads as the same product |
| `compare-14-alignment-saved-narrow.png` | 320, same basis |

## Named states

| File | State |
|---|---|
| `member-01-alignment-unsaved-desktop-1440.png` | Image 04, with `Save privately` live for the first time |
| `member-02-alignment-saved-desktop-1440.png` | `ALIGNMENT_SAVED` |
| `member-03-alignment-saved-mobile-390.png` | Saved at 390 |
| `member-04-alignment-saved-narrow-320.png` | Saved at 320 |
| `member-05-alignment-stale-desktop-1440.png` | `SAVED_STALE` — one cited evidence record has moved from Version 3 to Version 4 underneath the saved result |
| `member-06-alignment-stale-mobile-390.png` | Stale at 390 |
| `member-07-alignment-filtered-desktop-1440.png` | The filter row applied (Partially supported), filtering rows inside BOTH status cards while the summary totals stay unfiltered |
| `member-08-alignment-filter-empty-1440.png` | A filter that matches nothing in a card: it says so rather than leaving an empty table under a heading |
| `member-09-saved-details-desktop-1440.png` | `View saved details` — the versions list, the pinned evidence and excerpts, the member's own response context |
| `member-10-saved-details-mobile-390.png` | Saved details at 390 |
| `member-11-saved-details-narrow-320.png` | Saved details at 320 |
| `member-12-delete-confirm-desktop-1440.png` | The delete confirmation, which says exactly what goes and what is not affected |
| `member-13-delete-failed-desktop-1440.png` | Image 09-d over a slate that is visibly, completely still saved |
| `member-14-delete-failed-mobile-390.png` | Delete failure at 390 |
| `member-15-alignment-saved-200pct-zoom-640css.png` | 200% zoom at 1280 (640 CSS px), WCAG 1.4.10 reflow |
| `member-16-save-failed-beside-saved-1440.png` | **New, finding F2.** A save that failed while a saved slate exists. The failure card and the green saved banner render together, and now agree: "Nothing new was saved. Your saved slate is unchanged." beside "Saved privately · Current for these inputs" |
| `member-17-save-failed-beside-saved-390.png` | The same at 390 |
| `member-18-saved-details-truncated-1440.png` | **New, finding F5.** 64 saved versions with the rail listing 50. The rail says "Showing the 50 most recent of 64 saved versions." and the delete confirmation says "This removes all 64 saved versions" |
| `crop-stale-rail.png` | The stale truth card at rail width — the one composition correction this slice made after rendering it (see below) |

## Measured verification

| Check | Result |
|---|---|
| Workbench proportion at 1440 | 844px = **58.6%**, rails 235/211 — identical for unsaved, saved and saved details. Image 04 measures 58.6% |
| Horizontal overflow | Clean at 320/360/390/430/480/560/640/700/768/900/1024/1100/1200/1280/1366/1440/1600 across saved, stale, filtered, saved-details and delete-failed |
| Contrast | **No failures** at 1440/390/320 on all five screens |
| Touch targets | No focusable target below 24×24 CSS px. The three native radios in OS-3's response rail measure 13×13 as glyphs, but each is wrapped in a `<label>` whose box is 303×73 at 390, so the target the member hits is the label. Pre-existing OS-3 markup, unchanged here |
| Heading order | Saved details: `h1` Saved · Saved slate → `h2` Saved qualifications → `h3` What this saved result holds. The alignment screen keeps OS-3's `h1` → `h3` structure unchanged (noted, not altered — it is not this slice's file to churn) |
| Honesty states | The public preview renders no save control and says saving arrives with membership; a newer unsaved analysis never shows the saved banner; a stale result never says "current"; a failed delete leaves the slate visibly saved |
| No score/verdict | No percentage, ratio, ranking, recommendation or verdict on any saved surface, asserted over the room markup at three viewports |
| Dark theme | No new dark rules; the site-wide pause is respected |
| `--os-card-gap` | **Unchanged.** The written 12px rule and the images' measured ~24–28px disagree, and that is an open owner decision across all four primaries. This slice does not settle it by stealth |

## Corrections made after looking at the renders

1. **The stale chip ran out of its card.** `Inputs changed · Reanalysis
   required` is half again as long as the current-state chip, and image 09-c
   holds it on one line inside a card three times the width of our rail. With
   `white-space: nowrap` it bled over the workbench. The stale chip now wraps
   inside the pill; both facts stay in one pill, which is the authority's
   point — they are one state, not two. (`crop-stale-rail.png`)
2. **The saved footer's truth block was too narrow.** Image 04's 22rem measure
   is right for its short sentence and wrong for image 05's two full lines; the
   saved variant takes 28rem, which produces image 05's two-line block instead
   of four.
3. **`Review inputs` was duplicated in the saved footer.** Image 05 carries
   exactly two actions there and keeps `Review inputs` in the context strip.
   Removed from the saved footer; kept in the stale footer, which is where
   image 09-c lists it.
4. **The `All` filter tab was a 17px target.** Given horizontal padding, with
   the row gap reduced by the same amount so the drawn rhythm still matches
   image 05's ~34px between labels.
5. **The context-strip link was a 20px line at 320.** Given a 24px minimum
   height without moving its baseline.

## What the review changed in this set

The 2026-08-04 independent review found one thing wrong with the evidence
itself (F8) and three things wrong with what the screens said (F2, F3, F5).
All four are visible here.

1. **Every `member-*` frame is re-captured against the real signed-in shell**
   (F8). Nothing else about them changed; the workbench, the rails and the
   measurements below are the same build.
2. **The versions list distinguishes its versions** (F3). The review's own
   copy of `member-09` showed two entries with byte-identical text — source
   version, save minute and qualification count are all shared between two
   saves of the same inputs. Each entry now leads with `Save N`, which is
   unique per slate by construction, and carries the source version and count
   below it. `member-09/10/11` and `member-18` show it.
3. **A failed save no longer says "Nothing is saved yet." to a member who has
   a saved slate** (F2). `member-16/17`.
4. **The versions rail says when it is truncated, and the delete confirmation
   counts every version rather than the listed ones** (F5). `member-18`.

Re-measured after the re-capture, on all seven rendered states: no horizontal
overflow at any of the 17 sweep widths, no contrast failure at 1440/390/320,
and no focusable target below 24×24 CSS px except the three pre-existing OS-3
native radios (13×13 glyphs inside 303×73 labels). Heading order unchanged.

The SQL corrections (F6, F7) have their own record: the migration header's
"RE-GATED 2026-08-04" block, and the five re-gate transcripts committed here
under `sql-regate/` — the first gate's own logs were only ever local, and a
finding reproduced on a real engine deserves a durable transcript.

| File | Stage |
|---|---|
| `sql-regate/regate-stage-1-chain-and-upgrade.txt` | The whole chain, OS-1 → OS-2 → OS-3 → OS-4, with the byte-for-byte member-content digests at each step |
| `sql-regate/regate-stage-2-exercise-and-rollback.txt` | Negatives, save, replay, currency, lifetimes, delete, isolation verifier, rollback, re-apply |
| `sql-regate/regate-stage-3-findings-f6-f7.txt` | The Moment-kind currency guard, and the concurrent same-key saves |
| `sql-regate/regate-stage-4-f7-race-before-and-after.txt` | The F7 race against the PRE-FIX procedure (4 of 5 raised) and against this one (0 of 5) |
| `sql-regate/regate-stage-5-final-bytes.txt` | Rollback and re-apply on the exact committed bytes |

## Honest limits

- There is no mobile or narrow authority in the locked set, so the 390 and 320
  sheets answer "does it read as the same product", not "does it match".
- The saved-details screen has no image authority at all (§14-M13a). It is
  built strictly from the room's established grammar and introduces no new
  composition, hierarchy or interaction language, but Pete has not seen it
  before and it is the item in this set most in need of his eye.
- Pete's visual acceptance has not been given. Nothing here is deployed and
  the feature flag remains off.
