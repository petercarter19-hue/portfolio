# PS-COMMUNITY-TABS-001 — QA evidence record

**Status:** Capture record prepared; update the marked capture fields only
after the final browser matrix has completed against the review commit. Until
then this is a reproducible test protocol, not a release certification.

## Runtime and review commit

| Field | Required final value |
| --- | --- |
| Branch | `work/2026-07-21-community-tabs-impl` |
| Review commit, full SHA | _Pending final review commit_ |
| Base commit, full SHA | `936d08dcb85fbb86da181600475aab398f68f979` |
| App origin | `http://127.0.0.1:5055` |
| Browser / version | _Pending browser-session capture_ |
| Capture mode | In-app Browser, fresh route load unless noted; calibrated same-origin harness only where needed to correct its 2× render / 1× output defect. |
| Fixture mode | Sample Community fixture; no authenticated data, writes, or feature-flag enablement. |
| Console result | _Pending final browser capture; required: zero errors_ |
| Network result | _Pending final browser capture; required: zero failed touched-flow static assets_ |

## Required capture matrix

For every completed row, record the final screenshot path, file SHA-256, and
normalized-pixel SHA-256. A normalized-pixel hash means: decode to RGBA,
respect EXIF orientation, convert to sRGB, and SHA-256 the width, height, and
raw RGBA pixel bytes in row-major order. It identifies visual identity apart
from PNG/JPEG metadata or compression.

| ID | Route / start state | Action sequence | CSS viewport / DPR / theme | Required assertion | Screenshot / hashes |
| --- | --- | --- | --- | --- | --- |
| E01 | `/the-slate/break` direct | Fresh load | 1440×1000 / 1 / light | Direct The Break starts selected; exactly Feed + The Break appear; shared shell, rail, footer, and warm-light materials render. | _Pending final capture_ |
| E02 | `/the-slate` Feed | Click The Break once | 1440×1000 / 1 / light | Same response switches without reload; URL becomes `/the-slate/break`; only Break panel is visible. | _Pending final capture_ |
| E03 | `/the-slate/break` direct | Fresh load | 1440×1000 / 1 / dark | True dark canvas extends through Community content; no white application sheet; one-line desktop hero composition. | _Pending final capture_ |
| E04 | `/the-slate/break` direct | Fresh load | 390×844 / 1 / light | Two-tab rhythm, no overlap, no clipped text, and mobile card/reflow order. | _Pending final capture_ |
| E05 | `/the-slate/break` direct | Toggle theme, then settle | 390×844 / 1 / dark | Genuine mobile dark materials and readable contrast. | _Pending final capture_ |
| E06 | `/the-slate` Feed | Fresh load | 1440×1000 / 1 / light | Exactly two Community tab stops/labels; no Saved panel/tab/destination. | _Pending final capture_ |
| E07 | `/the-slate` Feed | Focus Feed; ArrowRight; ArrowLeft; Home; End; browser Back/Forward | 1440×1000 / 1 / light | Keyboard tab commands synchronize focus, selected state, URL, and visible panel. Back/Forward synchronize selected state, URL, and panel **without forcing focus**. | _Pending final capture_ |
| E08 | `/the-slate/break` | Activate Create a post; activate Back to the Feed | 1440×1000 / 1 / light | Create switches to Feed and focuses the actual composer; Back switches Feed rather than navigating to a dead target. | _Pending final capture_ |
| E09 | `/the-slate` Feed | Fresh load | 1078×900 / 1 / light | Catch Up rail remains visible as a separate 270px column; Feed main column does not underlap or clip it. | _Pending final capture_ |
| E10 | `/the-slate/break` | Attempt browser zoom to 200%; refresh/reflow | 1440 base viewport / 1 / light | **Conditional / browser-capability blocked:** the In-app Browser ignores Meta+ zoom (its `innerWidth` remains 1440 after reset plus five increments), so literal browser zoom cannot be certified here. Ask Pete to perform literal manual zoom or use another supported browser during owner review. | _No pass claim; see E10a_ |
| E10a | `/the-slate/break` | Set CSS viewport to the 720px effective width of 1440px at 200% | 720×900 / 1 / light | Functional reflow equivalent: one-column layout, no horizontal overflow/overlap, and operable controls. This is evidence of responsive behavior, not a substitute claim for literal browser zoom. | _Pending final capture_ |
| E11 | `/the-slate/break` | Attempt to emulate `prefers-reduced-motion: reduce`; interact with tabs | 1440×1000 / 1 / light | **Conditional / browser-capability blocked:** the In-app Browser cannot emulate the media preference. Static evidence confirms the scoped reduced-motion rule at `static/css/community-tabs.css:378–384` and focused regression at `tests/test_community_tabs.py:107–117`. Do not claim a live emulation pass. | _No pass claim; Pete/alternate-browser action required_ |
| E12 | `/the-slate/break` direct | Fresh load | 320×800 / 1 / light and dark | **Provisional pass; exact-review recapture pending:** after the scoped 12px link-gap correction, `Interview Studio` ends at x=300.945, leaving 19.055px trailing clearance; `document.scrollWidth == 320`; console errors/warnings are zero. Repeat against the final review SHA. | Earlier failure captures: `/Users/petercarter/.codex/visualizations/2026/07/21/019f8708-2314-7882-a562-66e3ad8b27ab/community-break-current/break-320-light-top.png`, `break-320-dark-top.png`; exact-SHA hashes pending |
| E13 | `/the-slate` Feed and `/the-slate/break` direct | Fresh load; then Feed → The Break | 1440×1000 and 390×844 / 1 / light and dark | **DOM pass:** fresh Feed has all 3 Break images deferred through `data-*` attributes and native Break `src`/`srcset` count 0; Feed first image is responsive eager/high/async and lower Feed images are responsive lazy/low/async. After Break click and on direct Break, hero is responsive eager/high/async and both lower images are responsive lazy/low/async. **Resource Timing subcheck conditional:** this browser does not expose the Resource Timing API, so no runtime request-list pass is claimed. | Manager DOM capture passed; Resource Timing API unavailable (Conditional). |
| E14 | `/the-slate` Feed | Composer → attach Photo → AI review → Publish update | 1280×720 / 1 / light | **Mouse/viewport pass:** review dialog is y=24–696 (672px), its review body exposes internal overflow (`clientHeight=588`, `scrollHeight=752`), and Publish is fully visible at y=631–679. Real locator click publishes `p-published-1` with mountain-ridge WebP and closes the overlay. **Keyboard subcheck Conditional:** the IAB CUA's native Tab remains at the textarea; static focus-trap guard is covered by test, but no live keyboard pass is claimed. | Manager live retest pass for geometry/mouse; CUA Tab capability conditional. |

## Deterministic non-browser checks

These checks ran from the target worktree after the implementation and the
1078px regression guard were added.

| Check | Result |
| --- | --- |
| `git diff --check` | Pass |
| `python -B -m unittest tests.test_community_tabs tests.test_navigation -q` | Pass: 31 tests. |
| `python -B -m unittest discover -s tests -t . -q` | Pass: 795 tests, 2 skipped. |
| `node --check static/js/community-tabs.js && node --check static/js/feed-living-stream.js` | Environment gate open: shell returned `zsh: command not found: node`. Browser-native parse/behavior evidence is required instead; do not treat this as waived. |
| Bundled runtime `node --check static/js/community-tabs.js && node --check static/js/feed-living-stream.js` | Pass after the responsive-media and hydration changes. |
| Node-backed import parse | Both files parsed; execution stopped only at expected `ReferenceError: document is not defined` outside a DOM. |
| Live route probe | `GET /the-slate` 200; `GET /the-slate/break` 200; `GET /the-slate/saved` 302 with `Location: /the-slate`. |
| Touched static probe | _Repeat against final server_: Community CSS/JS, 18 raw sources, and 36 responsive WebP delivery derivatives must return HTTP 200. |

## Manager browser-semantics ruling

**E07, 2026-07-21:** The manager verified ArrowRight, ArrowLeft, Home, and
End synchronize focus, selection, URL, and visible panel. Browser Back and
Forward synchronize selection, URL, and visible panel but intentionally retain
the browser's existing focus instead of stealing it. This is the expected
history behavior; it is not a focus failure and requires no code change.

**E10, 2026-07-21:** The In-app Browser ignores browser-level Meta+ zoom:
after reset and five zoom-in increments `innerWidth` remained 1440. Literal
200% zoom is therefore Conditional/blocked by browser capability, not passed.
E10a records the 720px CSS-viewport reflow equivalent separately. Pete must
either perform literal manual zoom at review or direct capture in a browser
that exposes a verifiable zoom level.

**E11, 2026-07-21:** The In-app Browser cannot emulate
`prefers-reduced-motion`. Live media-preference behavior is therefore
Conditional/blocked, not passed. The static reduced-motion implementation is
at `static/css/community-tabs.css:378–384` and is pinned by
`tests/test_community_tabs.py:107–117`; a literal media-emulation check remains
for Pete or an alternate supported browser at owner review.

**E12, 2026-07-21:** Initial 320px light and dark captures failed visually:
the shared-header `Interview Studio` label clipped even though document
horizontal overflow was zero. Its measured right edge was x=316.95, which left
only 3.05px in a 320px viewport. The Community-scoped 320px header gap was
reduced from the inherited 20px to 12px. The fresh manager check measured the
label's right edge at x=300.945 (19.055px clearance), `scrollWidth == 320`, and
zero console warnings/errors: **provisional pass**. A new light/dark pair must
still be hashed against the final review SHA.

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
