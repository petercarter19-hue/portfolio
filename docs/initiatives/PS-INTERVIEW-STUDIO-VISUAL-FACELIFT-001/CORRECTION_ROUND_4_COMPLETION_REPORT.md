# Round-4 completion report — facelift retired, two surviving changes

- **Package:** PS-INTERVIEW-STUDIO-VISUAL-FACELIFT-001
- **Writer:** Claude (Fable 5), single writer, complete-diff self-review done
- **Date:** 2026-08-01
- **Branch:** `work/2026-08-01-interview-me-facelift-correction-001`
- **Base:** `42d0213` (package activation on `origin/main` at `2494aa7`)
- **Final:** `0ec187c` plus this report
- **Release state:** local worktree only. Not pushed, no PR, no pipeline, no
  deployment. peerslate.com is unchanged.

## Owner decision

After reviewing the round-3 build in a live browser (2026-08-01, local
server), Pete retired the facelift direction entirely: "go back to what's on
the actual site itself." The round-3 implementation (left tools rail,
microphone hero, three-column shell, smoky-teal/champagne dark, depth pass)
was reverted to the released base. The twelve locked PNGs remain in the
package as historical visual authority for a direction the owner has
withdrawn; they no longer describe intended runtime state.

Two changes survive, both owner-directed in the same session:

1. **Session editing in the rail (Interview Me).** The right-rail Session
   card repeated the summary that the top "Edit session" bar already showed.
   The card now owns the live Experience / Question family / Session selects,
   moved — not copied — from the bar. The bar is hidden wherever it owns no
   control and remains in Interview AI, which still owns the answer-source
   select. The released rail tuck offsets were removed so each rail starts
   level with its task stage; without that, the rails slid under History.
2. **Interview AI desktop overlap fix.** A released desktop rule pulled the
   AI rail out of the grid (`position: absolute; top: -8rem`) over a
   full-width form, clipping "Different question" and "Create question".
   The rail returns to its grid area; the form gets its own column. This
   defect is live in production today and this branch is currently the only
   fix for it.

## Changed paths (vs base 42d0213)

- `templates/interview_studio.html` — selects moved bar→rail card; no other
  markup change
- `static/css/interview-studio.css` — two appended sections (+69 lines)
- `tests/test_interview_studio.py` — two tests updated to assert the new
  control placement instead of the old sibling order

No JavaScript change. No route, endpoint, payload, prompt, storage key,
media, score-meaning, theme-persistence, or privacy-copy change.

## Verification

- Focused suite: 158 passed. Full suite: 1076 passed, 2 skipped.
- Live browser at 1536×1024: full Interview Me flow (type → review 62/100 →
  rail state switch), session selects drive question/queue/counter correctly,
  Interview AI question controls fully visible, Video Practice and History
  unchanged, dark theme, 768 and 390 widths, no horizontal overflow, no
  console errors.
- Served HTML renders `data-is-active-mode` server-side, so the AI session
  bar is correct on direct `?mode=ai` loads before JS runs.
- Trade-off accepted by owner: Experience / Question family are edited from
  the Interview Me tab; Interview AI and Video Practice no longer show those
  controls.

## Honest limits / next step

- Owner acceptance of the two surviving changes is pending Pete's local
  review (server at 127.0.0.1:5093, LAN 5094).
- On "ship it": push branch, open Azure DevOps PR, pipeline, then production
  smoke of `/interview-studio?mode=me` and `?mode=ai` (the AI overlap fix is
  the user-visible production change to verify live).
- `CURRENT_BASELINE.yaml` package status should be updated at merge time to
  record the retired visual direction and the shipped scope.
