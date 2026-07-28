# Measured Visual Evidence

## Evidence state

- Route: `http://127.0.0.1:5018/petec/resume`
- Source branch:
  `work/2026-07-27-overview-live-fidelity-correction-001`
- Original implementation base:
  `f85747275b81359c0d99bd99f340e65aa58420b8`
- Release integration base:
  `49072ef2af7c3268bc06ee5e51c9133b9b33c259`
- Browser: headless Chromium at device scale factor 1
- Page scale: normal CSS geometry; no `zoom` or transform fitting
- Owner acceptance: passed on 2026-07-28

## Authority comparison at 1535x1024

The target positions are measured from
`ask-pete-ai-overview-open-desktop-2026-07-26.png`. Small target ranges reflect
anti-aliasing and the fact that the authority is a raster reference.

| Region | Authority target | Corrected browser measurement |
|---|---:|---:|
| Shared header height | about 102px | 102.38px |
| Full shell | about x14, 1502px wide | x16, 1503px wide |
| Left rail | about 154-160px | 160px |
| Center stage | x208, about 960px | x208, 959px |
| Public AI rail | about 320px | 320px |
| Hero opening | about 309px high | 308px |
| Portrait | about 270x288px | 272.30x288px |
| Member name | about x530 / 34px | x530.88 / 34.4px |
| Hero supporting copy | about 12-13px | 12.48px |
| Proof value | about 30-32px | 30.7px |
| Story band top | about y427 | y426.56 |
| Story band | about 176px high | 176px |
| Career block | about 345px high | 344.80px |
| Story + Skills | content-dependent | 242.91px |
| Credentials | content-dependent | 163.03px |
| Philosophy band | about 112px high | 112px |
| Closing / future band | about 132px high | 132px |
| Résumé transition | about 36px high | 36.02px |

## Typography measurements

The corrected desktop type is intentionally compact. Computed values at the
authority viewport are:

| Element | Font size | Line height |
|---|---:|---:|
| Platform navigation | 14.88px | 23.81px |
| Profile tab | 13.44px | 21.50px |
| Left rail navigation | 11.20px | 17.92px |
| Member name | 34.40px | 33.71px |
| Professional headline | 12.48px | 18.10px |
| Intro / location | 12.48px | 18.10px |
| Public contact line | 9.60px | 12px |
| Hero action | 10.24px | 16.38px |
| Proof value | 30.70px | 30.70px |
| Proof label | 9.60px | 11.71px |
| Section kicker | 9.92px | 14.38px |
| Story heading | 21.60px | 24.19px |
| Career title | 11.52px | 16.70px |
| Career summary | 9.92px | 12.90px |
| Skill | 10.56px | 15.31px |
| Credential title | 11.52px | 16.70px |
| Future heading | 21.60px | 24.19px |

At 1024px, the member name reduces to 28.8px and proof values to 19.2px so
the long `9 / $19.2M` value remains on one line. At 390px, the approved mobile
hierarchy uses a 32px member name, 26.4px proof values, and 12.48px body copy.

## Responsive geometry

| Viewport | Shell / center result | Rail state | Horizontal overflow |
|---|---|---|---:|
| 3840x2160 | 1504px shell / 960px center | both docked | 0px |
| 2560x1440 | 1504px shell / 960px center | both docked | 0px |
| 1920x1080 | 1504px shell / 960px center | both docked | 0px |
| 1535x1024 | 1503px shell / 959px center | both docked | 0px |
| 1440x900 | 1408px shell / 864px center | both docked | 0px |
| 1366x900 | 1334px shell / 790px center | both docked | 0px |
| 1312x900 | 1280px shell / 1088px center | AI undocked | 0px |
| 1024x900 | 992px shell / 800px center | left docked | 0px |
| 960x900 | 960px center | compact local row | 0px |
| 390x844 | 366px Overview card | compact local row | 0px |

The 1024px opening is separately measured at 240px high with a 234.08x224px
portrait, 28.8px member name, and 19.2px proof values. Its 800x1566.64px
Overview center is within roughly three percent of the authority's normalized
vertical density. The 390px opening starts at y124.59, uses a 366x232px
portrait, and reaches the story band at y827.

## Interaction measurements

- After the page scrolls 995px, both wide-desktop sticky rails remain at
  y102.39.
- Selecting Skills updates the URL to `#skills`, moves keyboard focus to the
  destination, and lands the section below the sticky header.
- Selecting Overview returns the page to scroll position 0 and restores the
  Overview current state.
- The compact Sections control opens as a visible grid.
- Choosing compact Skills closes the menu, updates the URL to `#skills`, and
  moves keyboard focus to the destination.
- Compact Ask Pete AI opens `#chat-panel` with `aria-hidden="false"`.

## Release integration recheck

After rebasing onto Azure `origin/main` at
`49072ef2af7c3268bc06ee5e51c9133b9b33c259`, the release candidate was
rechecked at 1535x1024 and 390x844. The automatic content-hash URL for
`resume2.css` was present, Technical Strengths and Story Chapters remained in
the accepted composition, the redundant left-rail Ask action remained absent,
and horizontal overflow remained 0px at both viewports.

## Local screenshot inventory

Final local evidence is under `output/playwright/correction6/`:

- `page-1535.png` and `center-1535.png`
- `page-1024.png` and `center-1024.png`
- `page-390.png` and `center-390.png`
- `metrics-1535.json`, `metrics-1024.json`, and `metrics-390.json`

Earlier wide-shell evidence remains under the local Playwright output tree and
was used to verify the 3840, 2560, 1920, 1440, 1366, 1312, and 960 breakpoints.
Only the named final evidence should be retained in a future review commit.

## Truth-preserving differences

The authority uses illustrative people, metrics, locations, career entries,
and media. The corrected browser result preserves the real approved public
projection instead of copying invented fixture content. The current shared
PeerSlate logo is also preserved because changing the global brand asset would
be a separate shared-shell visual decision.
