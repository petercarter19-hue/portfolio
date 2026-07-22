# PS-COMMUNITY-TABS-001 — QA evidence record

## Round 1 correction — current record

**Status:** Corrected implementation is committed and deterministic checks
pass. Fresh browser captures, Pete acceptance of the actual corrected pages,
the designated-manager audit, and fresh dual independent reviews are pending.
This is not a merge-readiness, release, deployment, or live-production claim.

### Exact implementation and sync record

| Field | Recorded value |
| --- | --- |
| Branch | `work/2026-07-21-community-tabs-impl` |
| Azure `origin/main` manager-seen commit | `d573b23d78eba1b398bb52952e695fe595d12d7b` |
| Pre-merge base | `d2592f08056e09629a302966b47fa8ff92517d8e` |
| Local no-rebase merge commit | `78f3b4658129cc0f86825a77a40764e6e56bec88` |
| Corrected implementation commit | `e6babaa9c04859c41dadfa83952ffca815c032ce` |
| Corrected implementation parent | `78f3b4658129cc0f86825a77a40764e6e56bec88` |
| Fixture mode | In-page sample only; no persistence, sharing, publication, Journal placement, connection, or feature-flag enablement. |
| Writer browser result | **Blocked:** Browser runtime initialized, but the available-browser list was empty. No screenshot was generated or reused by the writer. |

### Correction verification

| Check | Result |
| --- | --- |
| Break focus lifecycle | **Pass, automated behavior:** activating `Back to the Feed` while focus is inside Break focuses the visible Feed tab before Break becomes hidden. |
| Composer cancel | **Pass, automated behavior:** closing the first review returns focus to the connected composer invoker. |
| Review transition / Back / cancel | **Pass, automated behavior:** review-stage rerenders preserve the original logical return target; Back returns to editable review and later cancel restores the composer. |
| Local-preview completion | **Pass, automated behavior:** after the Feed rerender removes the old invoker, focus resolves to the new visible connected composer. |
| Preview truth | **Pass, static/fixture contract:** exact summary, primary label, result provenance, and completion announcement are present. False publication, private-Journal save, public-Journal placement, and completed confidentiality-check strings are absent. |
| Connection destinations | **Pass:** My Story, Slate Board, and Resume render as inert `preview · not connected` labels with no pressed/selected persistence state. |
| Legacy My Slate navigation | **Pass:** Community desktop/mobile navigation and Feed error recovery label `/the-slate/my-slate` as **My Slate**; `/app/journal` is not exposed while Journal remains off. |
| Focus behavior harness | **Pass: 4/4** (`tests/community_focus_lifecycle.test.js`). |
| Focused Community + navigation suite | **Pass: 37/37.** |
| Full repository suite | **Pass: 801 tests; 2 expected skips.** Expected negative-path warnings were unchanged. |
| JavaScript syntax | **Pass:** `community-focus-lifecycle.js`, `community-tabs.js`, and `feed-living-stream.js`. |
| Diff whitespace check | **Pass:** `git diff --check`. |
| Static asset probe | **Pass: 68/68:** 2 CSS, 3 JS, and 63 Community/Feed image files returned 200 through the Flask test client. |
| Product-image uniqueness | **Pass:** 18 production sources; closest 9×8 grayscale dHash distance is 19 (`break-chair-plant.png` versus `feed-workflow-closeup-2026-07-21.png`), above the duplicate threshold of 6. |
| Feature flags | **Pass:** `PEERSLATE_DATABASE_UI_ENABLED` and `PEERSLATE_JOURNAL_ENABLED` remain false by default. |

### Required fresh exact-SHA browser evidence

Every row below is **pending** at corrected implementation commit
`e6babaa9c04859c41dadfa83952ffca815c032ce`. A row may become Pass only after
the actual page is captured with viewport, theme, state, path, dimensions,
file SHA-256, and normalized RGBA SHA-256 recorded. One raster may not be reused
as two distinct proofs.

| ID | Required actual-page state | Status |
| --- | --- | --- |
| R1 | Break desktop 1440 light: opening/top and lower journey | Pending manager capture |
| R2 | Break desktop 1440 dark: opening/top and lower journey; E03 replacement must visibly include the real dark hero/top | Pending manager capture |
| R3 | Break mobile 390 light: opening and full lower journey | Pending manager capture |
| R4 | Break mobile 390 dark: opening and full lower journey | Pending manager capture |
| R5 | Feed Gallery desktop light/dark and mobile 390 light/dark | Pending manager capture |
| R6 | Feed Video desktop light/dark and mobile 390 light/dark | Pending manager capture |
| R7 | Corrected AI-assisted review modal with local-preview truth and reachable 720px action | Pending manager capture and focus transcript |
| R8 | Result after `Add preview to Feed`, showing `Local preview · not saved` | Pending manager capture and focus transcript |
| R9 | 320px header/reflow with truthful **My Slate** label where the Community mobile navigation is present | Pending manager capture |
| R10 | Break `Back to the Feed`, composer cancel, review Back/cancel, and preview completion visible-focus behavior | Pending manager browser interaction log |

Pete must see and accept the actual R7/R8 pages and representative corrected
Feed/Break pages before the designated manager begins the final audit and before
fresh dual independent reviews. None of those acceptances has been claimed.

### Superseded evidence exclusion

The Round 0 record below tested commit
`6815382646c36bfbd89f7a2ae02d519e92963de5`. Its external screenshots are
historical only and are excluded from Round 1 proof because they predate the
focus, preview-truth, and My Slate-label corrections. In particular, old modal
and result captures S12/S13 must not be reused, and old E03 cannot satisfy the
required fresh dark hero/top capture. The old external directory
`community-break-current/` is not the current capture root; the manager must
use a new exact-SHA directory and ledger.

## Round 0 record — superseded, retained for audit history only

**Status:** Evidence reconciliation for the tested implementation commit. This
record is not a release certification, merge-readiness decision, or live
deployment claim.

## Runtime and reviewed implementation

| Field | Recorded value |
| --- | --- |
| Branch | `work/2026-07-21-community-tabs-impl` |
| Tested implementation commit, full SHA | `6815382646c36bfbd89f7a2ae02d519e92963de5` |
| Base commit, full SHA | `936d08dcb85fbb86da181600475aab398f68f979` |
| App origin | `http://127.0.0.1:5055` |
| Browser / version | Codex In-app Browser; the browser version is not exposed by the available session UI. |
| Capture mode | In-app Browser, fresh route load unless noted; calibrated same-origin harness only where needed to correct its 2× render / 1× output defect. |
| Fixture mode | Sample Community fixture; no authenticated data, writes, or feature-flag enablement. |
| Console result | **Conditional:** manager observation for E12 was zero errors/warnings, but no direct console export for exact commit `6815382646c36bfbd89f7a2ae02d519e92963de5` was retained. HTTP and unit tests cannot prove browser-console cleanliness. |
| Network result | **Pass:** on 2026-07-22, the local server returned HTTP 200 for all 67 committed Community static assets (2 CSS, 2 JS, 63 images—including raw sources and WebP derivatives). The page emitted `community-break-3` four times. |

## Capture storage and hash method

The supplied manager captures are retained outside Git at
`/Users/petercarter/.codex/visualizations/2026/07/21/019f8708-2314-7882-a562-66e3ad8b27ab/community-break-current/`.
They are evidence artifacts, not product files, and therefore are **not retained
in this commit**. The capture ledger below records their actual file SHA-256,
dimensions, and normalized-pixel SHA-256 when the file remains available.

Normalized-pixel SHA-256 means: decode the PNG, respect EXIF orientation,
convert to sRGB RGBA (the supplied PNGs had no ICC conversion requirement),
prefix big-endian width and height, then hash the raw RGBA bytes row-major.
For interaction-only results with no captured raster, the matrix explicitly
says that no screenshot/hash was retained rather than inventing one.

## Browser evidence matrix

| ID | Route / start state | Action sequence | CSS viewport / DPR / theme | Result | Capture / evidence |
| --- | --- | --- | --- | --- | --- |
| E01 | `/the-slate/break` direct | Fresh load | 1440×1000 / 1 / light | **Pass:** direct Break starts selected; only Feed and The Break tabs render; shared shell, rail, footer, and warm-light materials are present. | S01 (manager visual capture; externally retained). |
| E02 | `/the-slate` Feed | Click The Break once | 1440×1000 / 1 / light | **Pass:** same-response switch reaches `/the-slate/break` and shows only the Break panel. | S02 (manager visual capture; externally retained). |
| E03 | `/the-slate/break` direct | Fresh load | 1440×1000 / 1 / dark | **Pass:** dark canvas extends through Community content with the intended one-line desktop hero composition. | S03 (manager visual capture; externally retained). |
| E04 | `/the-slate/break` direct | Fresh load | 390×844 / 1 / light | **Pass:** two-tab rhythm, card reflow, and readable light materials are captured without overlap or clipping. | S04 (manager visual capture; externally retained). |
| E05 | `/the-slate/break` direct | Toggle theme, then settle | 390×844 / 1 / dark | **Pass:** dark mobile materials and contrast are captured at the required viewport. | S05 (manager visual capture; externally retained). |
| E06 | `/the-slate` Feed | Fresh load | 1440×1000 / 1 / light | **Pass:** exactly two rendered Community tabs; the Saved address remains a redirect, not a panel or tab. | S06 plus focused route/accessibility tests (manager capture externally retained). |
| E07 | `/the-slate` Feed | Focus Feed; ArrowRight; ArrowLeft; Home; End; browser Back/Forward | 1440×1000 / 1 / light | **Pass:** manager verified key navigation synchronizes focus, selection, URL, and panel. Back/Forward synchronize state without stealing focus. | **Not applicable:** no single screenshot can prove this event sequence; manager interaction result is recorded below and focused static regression passed. |
| E08 | `/the-slate/break` | Activate Create a post; activate Back to the Feed | 1440×1000 / 1 / light | **Conditional:** focused tests verify the controls and implementation contract, but an exact-head browser action transcript/capture for both focus outcomes was not retained. No live-pass claim is made. | **Not retained in commit:** no manager screenshot or action log was supplied for this interaction-only check. |
| E09 | `/the-slate` Feed | Fresh load | 1078×900 / 1 / light | **Pass:** Catch Up remains a separate 270px rail and the Feed column does not underlap or clip it. | S07 (manager visual capture; externally retained). |
| E10 | `/the-slate/break` | Attempt browser zoom to 200%; refresh/reflow | 1440 base viewport / 1 / light | **Conditional / browser-capability blocked:** In-app Browser ignores Meta+ zoom; `innerWidth` remained 1440 after reset plus five increments. Literal 200% zoom is not certified. | S08 records the attempt; it does not turn the blocked subcheck into a pass. |
| E10a | `/the-slate/break` | Set CSS viewport to the 720px effective width of 1440px at 200% | 720×1000 / 1 / light | **Pass:** functional reflow equivalent is one column with no horizontal overflow/overlap and operable controls. This is responsive evidence, not literal zoom evidence. | S09 (manager visual capture; externally retained). |
| E11 | `/the-slate/break` | Attempt to emulate `prefers-reduced-motion: reduce`; interact with tabs | 1440×1000 / 1 / light | **Conditional / browser-capability blocked:** In-app Browser cannot emulate the media preference. Static evidence confirms the scoped rule and focused regression. | **Not applicable:** no emulated-browser capture exists because the capability is unavailable; no live emulation pass is claimed. |
| E12 | `/the-slate/break` direct | Fresh load | 320×800 / 1 / light and dark | **Pass (visual/header scope):** `Interview Studio` ends at x=300.945 with 19.055px trailing clearance and `document.scrollWidth == 320`. This row does not claim the separate global console result. | S10 light and S11 dark (manager visual captures; externally retained). |
| E13 | `/the-slate` Feed and `/the-slate/break` direct | Fresh load; then Feed → The Break | 1440×1000 and 390×844 / 1 / light and dark | **Pass (DOM attributes):** fresh Feed has all 3 Break images deferred through `data-*`; native Break `src`/`srcset` count is 0. First Feed image is responsive eager/high/async; lower Feed images lazy/low/async. Break click/direct load makes hero eager/high/async and lower images lazy/low/async. **Conditional (Resource Timing):** the browser exposes no Resource Timing API, so no request-list pass is claimed. | **Not applicable:** this is an inspected DOM/performance-property result; no screenshot is sufficient evidence. Manager DOM observation recorded below. |
| E14 | `/the-slate` Feed | Composer → attach Photo → AI review → Publish update | 1280×720 / 1 / light | **Pass (viewport and mouse):** review dialog is y=24–696 (672px); review body exposes `clientHeight=588`, `scrollHeight=752`; Publish is fully visible y=631–679. A real locator click publishes `p-published-1` with mountain-ridge WebP and closes the overlay. **Conditional (native Tab):** IAB CUA remains at the textarea; static focus-trap guard is covered, but no live keyboard pass is claimed. | S12 dialog and S13 published exact-head Feed capture (manager captures; externally retained). |

## Retained screenshot ledger

All paths below are relative to the capture-storage root stated above. File and
RGBA hashes were computed from the supplied files on 2026-07-22. Theme is the
manager/harness assertion associated with the named capture; a raster alone
cannot independently prove runtime theme state.

| ID | File / assertion | Dimensions | File SHA-256 | RGBA SHA-256 |
| --- | --- | ---: | --- | --- |
| S01 | `owner-gate-break-desktop-1440-light-corrected.png` — E01 light direct | 1440×1000 | `a4113f74428a290f8725de797f8f280e632ec0fe1410ced0da11a623ad441ae8` | `0fb36a6510d6806e05bf8914ce0c274952a4c919370fb5dd87ddffa973ec2185` |
| S02 | `break-desktop-1440-light-after-feed-click.png` — E02 Feed→Break | 1440×1000 | `7c41a6db671aec5bece7bcc58a92705c6b7f96acb13e34f080ac9f19f662729f` | `ac17a626d015da3cdb9579cc50adc4e38cbc80a17f28ba880d8fed291c6571b5` |
| S03 | `owner-gate-break-desktop-1440-dark-final-modules-corrected.png` — E03 dark direct | 1440×1000 | `363284026de8d921da941ea8cc92a279e6e03381b1e2578f5216d8dc2caf4604` | `9bf688086955cbe2c97a653711b282112dc627bb005cf6a34692ad3adcc4a96c` |
| S04 | `owner-gate-break-mobile-390-light-corrected-valid.png` — E04 light | 390×844 | `be5b50ee542aee02480495eae6ff4ad61d14644df7bad00c4cbdc2da84d529c3` | `8c0ddb3131333ca9e09e7a419e3a8ceef1b09a17821b4298fae72a9d37505239` |
| S05 | `owner-gate-break-mobile-390-dark-corrected-valid.png` — E05 dark | 390×844 | `9fc0c7ca16bd81db56641874a191cb1cc89fcf0bc48b958b22b48e3350eb2a60` | `d87418fb8c9470055938bf16722b83305b86131c7fd1d301294bd0958359a579` |
| S06 | `feed-desktop-1440-light-top.png` — E06 Feed | 1440×1000 | `dc52f0538c827bb0fe98d8104c2ef44d420b6d0113cab57694cf735f22b72cce` | `61a638aee04806ef4701b2fc054fdea399169f4a8b0b29a4c2d8d3d042329980` |
| S07 | `feed-1078-light-top.png` — E09 rail | 1078×900 | `1c0d5998bf4d8e25c6a5b7378e8e45912b106ca93a9918f12f2a7a360ca2be41` | `7aeff8ddfe503d08450090241a741ea22660d46a791da4f375b207ac2352018b` |
| S08 | `break-200-percent-zoom-light.png` — E10 attempted zoom | 1440×1000 | `bc566fca0e0a3bb39e6a791753dfbe19dacaaa2f715436c7af2bd0086a276022` | `90e4aa8c609e9675b28fe532b9f37a99c1033201d62bfa49f454cc391dad6c65` |
| S09 | `break-720-css-width-light.png` — E10a reflow | 720×1000 | `f9aa90c8f05749a7aa02f90a01f2b234065c3323b7b9c59c13334b5dfc58338c` | `a34caa92aed638d5b976937ba9398f753af6df0ae6ec279c7d8eb07c511a160e` |
| S10 | `break-320-light-top.png` — E12 light | 320×800 | `a4bbb68c7b79e184a72b9cb4219462e403ad079358469be2dc0101a0988feb3e` | `6ace26729eda2f886af5a0c793053c78ddeb679621bc7cb1e02eeee5824fe395` |
| S11 | `break-320-dark-top.png` — E12 dark | 320×800 | `a34b53642c4fcd2c95380fbe5b43108be57a2baedc1b8a3f687d729ee3d1a19e` | `9dca74448692e1865688dae2905ef1f3875f9bba59bfff7096a2acc8520e756f` |
| S12 | `modal-fix-1280x720-review.png` — E14 review dialog | 1280×720 | `fac44253e982a4d3167be725b0e1bef55f073da6aac3be8f7a9a1cac6ac24b90` | `e759c541f7b38ded77ee130e5f18fbf0027f602c5d66a412928c65e8652b3859` |
| S13 | `owner-review-feed-photo-published-6815382-light-mountain.png` — E14 post-publication, exact-head filename | 1280×720 | `f29a33f3c78f4c1a9d202eb8a0be3e4ee5a1ce6210265d9c5c755184de58300d` | `b8b060ac9ecc058b086439001e70a993ce7cf5520cc8e0e0ca522eebdf2107da` |

## Deterministic non-browser checks

These checks ran from the target worktree at the tested implementation commit
on 2026-07-22. Expected negative-path warnings in the full suite do not change
the successful final result recorded below.

| Check | Result |
| --- | --- |
| `git diff --check` | **Pass.** |
| `python -B -m unittest tests.test_community_tabs tests.test_navigation -q` | **Pass: 31 tests.** |
| `python -B -m unittest discover -s tests -t . -q` | **Pass: 795 tests, 2 skipped.** |
| Bundled runtime `node --check static/js/community-tabs.js && node --check static/js/feed-living-stream.js` | **Pass.** The shell has no ambient `node`; the bundled Codex runtime was used. |
| Node-backed import parse | **Conditional:** both files parsed; execution stops at expected `ReferenceError: document is not defined` outside a DOM. This is not browser-behavior evidence. |
| Live route probe | **Pass:** `GET /the-slate` 200; `GET /the-slate/break` 200; `GET /the-slate/saved` 302 with `Location: /the-slate`. |
| Touched static HTTP probe | **Pass:** all 67 committed Community static assets returned HTTP 200: 2 CSS, 2 JS, 63 images (raw and responsive WebP). No failed asset paths. |

## Manager browser-semantics ruling

**E07, 2026-07-21:** The manager verified ArrowRight, ArrowLeft, Home, and
End synchronize focus, selection, URL, and visible panel. Browser Back and
Forward synchronize selection, URL, and visible panel but intentionally retain
the browser's existing focus instead of stealing it. This is the expected
history behavior; it is not a focus failure and requires no code change.

**E10, 2026-07-21:** The In-app Browser ignores browser-level Meta+ zoom:
after reset and five zoom-in increments `innerWidth` remained 1440. Literal
200% zoom is therefore Conditional/blocked by browser capability, not passed.
E10a records the 720px CSS-viewport reflow equivalent separately. A literal
manual zoom check needs a browser that exposes a verifiable zoom level.

**E11, 2026-07-21:** The In-app Browser cannot emulate
`prefers-reduced-motion`. Live media-preference behavior is therefore
Conditional/blocked, not passed. The static reduced-motion implementation is
at `static/css/community-tabs.css:378–384` and is pinned by
`tests/test_community_tabs.py:107–117`; a literal media-emulation check needs
an alternate supported browser.

**E12, 2026-07-21:** Initial 320px light and dark captures failed visually:
the shared-header `Interview Studio` label clipped even though document
horizontal overflow was zero. Its measured right edge was x=316.95, which left
only 3.05px in a 320px viewport. The Community-scoped 320px header gap was
reduced from the inherited 20px to 12px. The manager measured the label's
right edge at x=300.945 (19.055px clearance) and `scrollWidth == 320`.
The visual/header result is Pass; the separate final exact-head console export
is Conditional as recorded above.

**E13, 2026-07-21:** Manager DOM inspection verified the stated responsive
loading attributes before and after activating The Break. Resource Timing was
unavailable in this browser, so runtime request-list evidence remains
Conditional rather than passed.

**E14, 2026-07-21:** The first 1280×720 composer review exposed two real
accessibility failures: the dialog was 833px tall with its top at -57.6px, and
Publish sat below the viewport; CUA Tab then cycled at Close. The correction
caps the dialog to the viewport, makes the review body internally scrollable,
and replaces the `offsetParent` focus filter with a visible-tabbable filter.
The manager's fresh live retest passes dialog geometry and mouse publication;
the IAB CUA native-Tab implementation remains stuck at textarea, so keyboard
traversal is explicitly **Conditional**, not a claimed live pass.

## Scope and truth checks

- The two first-class views are Feed and The Break. The Saved compatibility
  address redirects to Feed and is not indexed.
- A pre-existing per-post `Save` control remains a local Feed action only; it
  cannot reveal or navigate to a Saved Community view. Its regression check is
  in `tests/test_community_tabs.py`.
- No Break data API, database UI, Save to Board action, fake discovery route,
  fake poll write, or invented profile/count is enabled by this package.
- `PEERSLATE_DATABASE_UI_ENABLED` remains false by default. No feature flag
  changed in this lane.
