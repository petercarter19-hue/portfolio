# PS-COMMUNITY-TABS-001 — exact-SHA Community evidence recovery

**Status at generation:** Evidence recovered and hash-bound. This artifact did
not itself claim Pete acceptance, manager final acceptance, merge readiness,
deployment, flag enablement, or live production. Those later gates were
fulfilled by the combined milestone release; see
`../PS-COMMUNITY-JOURNAL-HOME-MILESTONE-001/RELEASE_CLOSEOUT_2026-07-23.md`.

## 1. Capture authority and truth boundary

| Field | Value |
| --- | --- |
| Product branch / rendered commit | `work/2026-07-21-community-tabs-impl` / `8326f2c3aff483f44822ae100d3dc1aedf42d437` |
| Product server | Local exact-SHA server at `http://127.0.0.1:8766` |
| Evidence package | `artifacts/ps-community-tabs-001/` |
| Durable capture manifest | `artifacts/ps-community-tabs-001/EVIDENCE_MANIFEST.json` |
| Fixture boundary | Sample Community only. No persistence, sharing, publication, Journal placement, connection, or feature enablement. |
| First-class views | **Feed** and **The Break** only. `/the-slate/saved` remains redirect-only and is never an evidence surface. |

The browser capture API emitted JPEG/JFIF bytes despite its `.png` filename
hint. The tracked PNGs are an exact decoded-RGB container conversion: Pillow
decoded each original JFIF stream to RGB and encoded that RGB into PNG. For all
15 pairs, the dimensions and decoded RGB bytes are identical; no resize, crop,
color adjustment, or content edit occurred. The original-stream hashes and
conversion lineage are recorded per raster in the manifest.

## 2. Stale-evidence failure and replacement

The previously tracked `artifacts/ps-community-tabs-001/*.png` set was invalid
for this product commit. It inherited screenshots from the older three-view
implementation; in particular, `desktop-1440-dark-break.png` showed a light
content canvas and a Saved surface. The old 11 PNGs were deleted, not renamed
or repurposed. All 15 current raster names carry route, state, viewport, theme,
and region fields and are listed in the manifest.

There are no retained Saved-page rasters, no stale implementation SHA claims,
no unqualified pending-browser rows, and no claim that a visual review has
already occurred.

## 3. Fresh integrated-page capture matrix

Every row is a distinct actual-page capture from the product commit above. File
and normalized RGBA SHA-256 values are in the manifest.

| Surface / assertion | Viewport and theme | Distinct captures |
| --- | --- | --- |
| Feed real loaded content (`Dinner has been served!` verified) | 1440×1000 light / dark | `feed__route-the-slate__state-loaded__vp-1440x1000__theme-light__region-top.png`; dark counterpart |
| Feed real loaded content | 390×844 light / dark | `feed__route-the-slate__state-loaded__vp-390x844__theme-light__region-top.png`; dark counterpart |
| Break direct opening | 1440×1000 light / dark | `break__route-the-slate-break__state-direct__vp-1440x1000__theme-light__region-top.png`; dark counterpart |
| Break restorative lower journey | 1440×1000 light / dark | `break__route-the-slate-break__state-direct__vp-1440x1000__theme-light__region-lower.png`; dark counterpart |
| Break opening and lower journey | 390×844 light / dark | four `break__route-the-slate-break__state-direct__vp-390x844__theme-…__region-{top,lower}.png` records |
| Break narrow reflow | 320×800 light / dark | two `break__route-the-slate-break__state-direct__vp-320x800__theme-…__region-top.png` records |
| Feed → Break keyboard action | 1440×1000 light | `break__route-the-slate__state-feed-keyboard-switch-focus__vp-1440x1000__theme-light__region-top.png`: Feed tab clicked, ArrowRight pressed, `/the-slate/break` reached, Break tab selected and visibly focused. |

The action-state capture is intentionally similar to direct light Break top
because it proves a focus-ring state in the same layout. It has a different
exact file hash and 37,135 changed pixels (2.58%); the manifest declares this
semantic-state exception to the coarse dHash collision instead of hiding it.

## 4. Interaction and accessibility evidence

- The action raster above proves the Feed → Break keyboard route, selection,
  and visible focus state in the actual page.
- `tests/community_focus_lifecycle.test.js` supplies the four behavior cases:
  Break → Feed focus return, composer cancel return, review Back/cancel return,
  and preview-completion focus after Feed rerender.
- Legacy Saved compatibility and the two-view route contract remain covered by
  `tests.test_community_tabs`.
- The capture tool did not export a separate browser console or network log.
  No clean-console or clean-network claim is made from these rasters; server
  route/static probes and deterministic tests are recorded separately.

## 5. Integrity audit

- Screenshot directory count: **15** PNGs.
- File SHA-256 uniqueness: **15 / 15**.
- Decoded normalized RGBA SHA-256: recorded for every raster.
- Perceptual audit: 9×8 grayscale dHash, threshold 6. The closest
  non-exception pair is distance **10**. The one declared distance-0 pair is
  the distinct keyboard-focus state described above; its exact hashes and
  pixel-difference evidence prove it is not a renamed duplicate.
- `tests.test_community_tabs` verifies manifest coverage, magic bytes,
  dimensions, file hashes, normalized RGBA hashes, and the declared focus-state
  exception against the committed evidence directory.

## 6. Deterministic verification

| Check | Result |
| --- | --- |
| `python -m unittest tests.test_community_tabs tests.test_navigation -q` | **Pass: 46 tests.** Includes the new committed-evidence manifest audit. |
| `python -m unittest tests.test_site_rules tests.test_governance_pointers -q` | **Pass: 33 guardrail tests.** |
| `ANTHROPIC_API_KEY=test-key-for-ci-only python -m unittest discover -s tests -t . -q` | **Pass: 810 tests, 2 expected skips.** The placeholder is process-only and no credential was read. Existing negative-path logs/warnings remain expected. |
| PNG signature, decode, dimensions, normalized RGBA and file hashes | **Pass: 15 / 15** against the committed manifest. |

## 7. Gates as recorded at generation, later fulfilled

At this evidence-recovery checkpoint, Pete acceptance, final audit, PR, merge,
deployment, and production verification were still future gates; this artifact
did not authorize them by itself. They were subsequently fulfilled on
2026-07-23: Pete accepted Community, the Claude Code audit of record passed,
Azure PR 161 squash-merged the accepted milestone, CI repair PR 162 merged,
pipeline 221 passed Build and Deploy, and live Feed/The Break verification
passed. The controlling release record is
`../PS-COMMUNITY-JOURNAL-HOME-MILESTONE-001/RELEASE_CLOSEOUT_2026-07-23.md`.
