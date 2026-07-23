# PS-COMMUNITY-TABS-001 — Visual authority and production asset manifest

**Recorded:** 2026-07-21
**Status:** implementation evidence. Rejected preview variants are not product
content, and source rasters remain preserved alongside delivery derivatives.

## Durable authorities

| Durable file | Source lineage | Dimensions | SHA-256 | Role / binding treatment | Status |
| --- | --- | ---: | --- | --- | --- |
| `owner-approved-dark-break.png` | `/Users/petercarter/.codex/generated_images/019f8708-2314-7882-a562-66e3ad8b27ab/exec-f3782c9a-9f4f-4a0d-83c7-932fc8e79e25.png`; supplied owner authority; prompt text was not supplied | 799 × 1969 | `e477540113683c8ad88be002e07940378957271d12e8aa6e2f9e2c837f974354` | Primary full-page authority. Controls dark canvas, sage/gold illumination, compact order, material depth, and imagery. Never product content. | Owner-approved |
| `owner-approved-light-break-2026-07-21.png` | `/Users/petercarter/.codex/generated_images/019f8708-2314-7882-a562-66e3ad8b27ab/exec-7ff64be3-6eb4-49ae-bac5-65023a206746.png`; supplied owner authority; prompt text was not supplied | 803 × 1959 | `67f70a978634febe95fbd1a401170b8553be554dd914db32925b2d46ba9b8517` | Required light counterpart. It has exactly the dark authority's layout and component structure; only warm-ivory/pale-sage color and contrast vary. Never product content. | Owner-approved, current |

An earlier unversioned light concept was explicitly superseded and is not
carried in this package. It must be disregarded for implementation or review.

## Source rasters and responsive delivery

The raw files in the first column are provenance records and are not rewritten.
Production markup serves the WebP derivatives below with explicit `srcset`,
`sizes`, intrinsic dimensions, `loading`, `decoding="async"`, and
`fetchpriority`. The mobile/desktop byte ceilings are respectively 120 KiB and
250 KiB; every listed delivery file is inside its ceiling. `dinner_served.jpg`
is explicitly retained byte-for-byte as the existing personal-photo fixture;
only the two adjacent delivery derivatives were added.

| Raw source / lineage | Role and corrected fixture identity | WebP delivery: dimensions, bytes, SHA-256 |
| --- | --- | --- |
| `static/images/community/break-chair-plant.png` — `exec-c6becc91-b0a1-4e3f-b558-57f6b3ec0fc9.png`; 1693 × 929; `414d143d5cf6e8781fa7c2e380ce93e30009a123fdafe3907b1af129b4ae4bb5` | Break hero; cover, 76% center focal point. | `break-chair-plant-640.webp`: 640 × 351, 6,424 B, `44b6034e968b8af95ecb7f276dcb7fba6eb1cdc65f15e7593400cc6d8b67b5a3`; `-1280.webp`: 1280 × 702, 19,100 B, `c4c676ebe99da283d8b73fb1ac7ea6bd77d87ad4a3c309e4abaff64d9776bcd6` |
| `static/images/community/break-transformation.png` — `exec-5990886b-4d50-425a-a435-de5240ad9cbd.png`; 1619 × 971; `d428c1582b83a9a51f7092674bf78fb8148c136252a9d62c0a304ee509f13121` | Break before/after card; full paired composition, center. | `break-transformation-640.webp`: 640 × 384, 17,220 B, `432333592c54d8a056354c70e2ec501dcd0629b0c3698e57521e302a1d24bab2`; `-1280.webp`: 1280 × 768, 48,020 B, `57cfa43aa6743b7b4213502dfb690f37bc7b42b038d13221ce71ce1394321081` |
| `static/images/community/break-bookstore.png` — `exec-650de25c-e376-460f-82c1-543926eb5f44.png`; 1672 × 941; `ea75cfed34f61394d1696a86bbf0fd42b3a49afcfee3ce0e7e42c2fbaf24c305` | Break Local Discovery; cover, 58% 48% desktop / 55% 48% mobile. | `break-bookstore-640.webp`: 640 × 360, 36,006 B, `3699922f63661a7761f51aff7fac0bcbae2b6a5be87bf89d695f1643b7f1d821`; `-1280.webp`: 1280 × 720, 88,524 B, `ee7240e9847a5761c1fcf478332ecd21198359917a3cfe824d22b2f506059b36` |
| `static/images/feed/dinner_served.jpg` — existing retained fixture; 2000 × 1500; `48a081bb8efebfc04b6a2e44832192a0dc117bdb9237cdd8cff0c5bfcd0fe2d8` | `POSTS_DEFAULT` → `p-pete-dinner`; only active above-fold Feed primary, high priority. | `dinner_served-640.webp`: 640 × 480, 54,342 B, `4a899369bf4278562ae9f3fe78bbe16aa5c93e60c5c96dc43fde4135878b7d2c`; `-1280.webp`: 1280 × 960, 162,114 B, `b3dc95efc5b35bee565028ae27a0daabd1c7c4d0112f5155c010cde316c9428b` |
| `static/images/feed/feed-workflow-whiteboard-2026-07-21.png` — `exec-e9d51184-512f-4c62-a21c-5064de715b9d.png`; 1672 × 941; `5be58b2bc06a194e849eede70af81e6d1e52e485f784a9bf3d623412ef8a039f` | `POSTS_DEFAULT` → `p-danielle-review`; retain people and board around 52% 45%. | `-640.webp`: 640 × 360, 20,408 B, `0a56fd2bf2eb27776369b1be4749ef1c4f485f9b63025e9599b822db12135d4d`; `-1280.webp`: 1280 × 720, 48,654 B, `205f1d0232780a62e886a9fb14782da01c1ae155adc65f37b2a185d79dc970c9` |
| `static/images/feed/feed-surf-sunrise-2026-07-21.png` — `exec-b1209ece-93eb-4a32-a566-2f6fbb23af4c.png`; 1672 × 941; `e6d937c17ce94a5eb4b8bae0b79767682968cc7300bbf2470517f75511df6277` | `POSTS_DEFAULT` → `p-marcus-surf`; centered surfer and horizon. | `-640.webp`: 640 × 360, 22,282 B, `68096811c8d2068362858807d590022e47477ccd484fd866d89c5415de56ddff`; `-1280.webp`: 1280 × 720, 63,194 B, `ccc22f9897e57b8e9fda781ed1ab8007f5b6e92a47fe2418cbdfc633789eccb4` |
| `static/images/feed/feed-team-demo-2026-07-21.png` — `exec-d7ca888f-fb9f-4290-8918-13fda5696330.png`; 1672 × 941; `9c3770a51d6073a32dcb46d24bfa739a807911eb7f44f7199b2bb222bd112d59` | `POSTS_DEFAULT` → `p-alex-demo` and simulated publish-video fixture; retain all teammates/model. | `-640.webp`: 640 × 360, 18,192 B, `78f4b6369cbeee966b62ec9f8d8b88684307729bf849d580ca583b6495862830`; `-1280.webp`: 1280 × 720, 45,212 B, `f9c4c2d70cea31e5ff548331ccbffbcd3045d4ed4d87795d6226442c4c0e1428` |
| `static/images/feed/feed-trail-run-2026-07-21.png` — `exec-e6f3eeb0-d282-4599-ba7e-c5ee478c1a9b.png`; 1672 × 941; `7cdb0b275090301cca2b84448c3c34dce3e9182f17a990b8f1b47c904d3bc0ec` | `POSTS_DEFAULT` → `p-marcus-5k`; runner at center/right. | `-640.webp`: 640 × 360, 21,350 B, `591de0c1b36959ff91232b2d84c94cc2bde63730331e4574f0edc59b3b683916`; `-1280.webp`: 1280 × 720, 52,878 B, `a0e394a6876e6198876a7908847e89c905d048885387631377c24c0f05edc7bc` |
| `static/images/feed/feed-coffee-notes-2026-07-21.png` — `exec-4d52e8a5-19f9-451b-b1f4-57459f64589d.png`; 1672 × 941; `582a459c8f91f7f2e51110c5efd16fb8778c7f5e1c9843bb57ca2b2b96e6a211` | `POSTS_DEFAULT` → `p-aisha-notes`; polaroid retains mug and notebook. | `-640.webp`: 640 × 360, 23,026 B, `6598452e2ec199ef50e21294e5d50e5c99e958031d4962505cf9d24a8fc691e2`; `-1280.webp`: 1280 × 720, 95,880 B, `9372f832921000e53e711a50d538e24cc08c9521294c7f9b2812a94ac34d7acf` |
| `static/images/feed/feed-keyboard-build-2026-07-21.png` — `exec-fd0eca30-5415-4beb-982c-729238e97b31.png`; 1672 × 941; `2097cff5dc3fe2549adc5496ca14d584a74bb108b41ae2b8faa44b6eae0a85b0` | `POSTS_GALLERY` → `p-jordan-keyboard`, first cell. | `-640.webp`: 640 × 360, 32,610 B, `a32d207c78b46b2df223fbf674ff90d7f994ef65a85e7bde4e726f061c54997b`; `-1280.webp`: 1280 × 720, 81,372 B, `546bac75be2352a40a7ff29b593aa032a75eb75b3e78b93bc1406c97943a8f7d` |
| `static/images/feed/feed-keyboard-components-2026-07-21.png` — `/Users/petercarter/.codex/generated_images/019f8708-2314-7882-a562-66e3ad8b27ab/exec-eb8a77da-a0d2-4840-8a2f-eb151c426d9b.png`; 1672 × 941; `037e84c82cee1cf789154740dce59ea3389c9ad68a1afb99021747b8ad1989b5` | Distinct owner-approved replacement for the formerly duplicated third `POSTS_GALLERY` → `p-jordan-keyboard` cell; tactile keyboard components/workbench, not the prototype-table scene. | `-640.webp`: 640 × 360, 31,178 B, `3fd12be51bab7ae9117a454fd8a56a031b0278c93822af0226f8b652f4c24333`; `-1280.webp`: 1280 × 720, 84,256 B, `567a55b734e924fac4dd155b9e7fb5b5d4a826faf4619c92980372f8f5c2406c` |
| `static/images/feed/feed-mountain-hike-2026-07-21.png` — `exec-89199731-8445-4965-a374-f3fcc9588179.png`; 1122 × 1402; `d9e5630ffd17031f365d1b78dc99f079b89b16c1cccd97aa9fa8060cf804a858` | `POSTS_DEFAULT` → `p-jordan-summit`; polaroid retains hiker/valley. | `-560.webp`: 560 × 700, 41,976 B, `947e7e0c9aba4bc8a5ba3e4bab05f44444626b87c95301bd716c7be698baed8e`; `-1120.webp`: 1120 × 1400, 113,360 B, `c347a4b1d33dc1b46af48fade892543751fe619b97fc2bb64774320efffb4289` |
| `static/images/feed/feed-prototype-table-2026-07-21.png` — `exec-fb0dc9ff-c85f-4b04-a7d3-fe671ee915a8.png`; 1672 × 941; `124a09d585599b212c2d8fb09dc6e162e55abd313f94a0fd7135755213540929` | Replacement for legacy `office_prototype.jpg`: `p-danielle-screens` first Gallery cell and the equivalent Rail fixture identity. It no longer appears in `p-jordan-keyboard`. | `-640.webp`: 640 × 360, 20,548 B, `e4b75c0ccbb2a4e827a92d4620a057a7f892be2f47dee8fcb7f81f29cbd6eeee`; `-1280.webp`: 1280 × 720, 49,754 B, `609ce554ae59d58354893d6afbfbff662d65b89c948ccb1162482bfd5ab51871` |
| `static/images/feed/feed-workflow-closeup-2026-07-21.png` — `exec-e868ea62-2369-44ac-95bc-4a80e13e87ad.png`; 1672 × 941; `e08eaf517f6028a2e2d9e0623890acb3b3a563ba5348d97634b6a519679cf324` | Replacement for legacy `whiteboard_close.jpg`: Gallery second-cell alternate fixture identity. | `-640.webp`: 640 × 360, 11,472 B, `f9ae602322c6448b9fade8007a0d1c3c4be2b6d6aaf6c74c3d237c489d36546e`; `-1280.webp`: 1280 × 720, 24,788 B, `37537c2263932f9bf22ea543bb1cf5eb5488ee3f623054bdd2a426f9e2fbcdd4` |
| `static/images/feed/feed-workflow-corkboard-2026-07-21.png` — `exec-72d49b7b-d4cd-47b3-8dd0-21d2a00221c6.png`; 1672 × 941; `3c80e764645b95574ca88c0585151bcb620cabe7cc8adcc7f67bd926fb9b08d8` | Replacement for legacy `work_whiteboard.jpg`: Gallery third cell, Rail alternate state, and detail fixture. | `-640.webp`: 640 × 360, 23,236 B, `816cd5b8e03c9257b69444b5a579573cc77c582b76fa29db324154602b6e0040`; `-1280.webp`: 1280 × 720, 68,992 B, `c3c461c42dc16c9f01207674bba50990e1f749068c4ea50c1e49b8a1d86df38f` |
| `static/images/feed/feed-surf-wave-2026-07-21.png` — `exec-4500bd20-edaf-489a-abbb-58100a6ffce8.png`; 1672 × 941; `a12ba7090ad4f48ef91fe1c382be460d4f457c6a4b9891315cf2d280bdd13152` | Replacement for legacy `surf_morning.jpg`: `POSTS_VIDEO` → `p-marcus-video`. | `-640.webp`: 640 × 360, 15,164 B, `700a912ef9c8b8ceee56d3ff3ca8c6cd41ff72ccb7c067291063602f659b17d4`; `-1280.webp`: 1280 × 720, 43,778 B, `4c937de3ea3842b9d52891aef44480c0ab9056b0363eb63f057e64e4c82b58af` |
| `static/images/feed/feed-journal-notebook-2026-07-21.png` — `exec-4b2f0472-f5cb-488d-b7a3-50f84ee6bf0c.png`; 1672 × 941; `37c7fb7d7fb0b54eb925555c49c69559b4dfbefc04ed4c94b65a7e3ddf0dda6a` | Replacement for legacy `coffee_notes.jpg`: `POSTS_GALLERY` → `p-jordan-keyboard`, second cell. | `-640.webp`: 640 × 360, 14,520 B, `82865d385adc8f486065a5bb6fa6e323a7460a889ae88b6b38a12c1540f99b53`; `-1280.webp`: 1280 × 720, 46,072 B, `610a22ba0caa0a47d1578f65809a20abf9182ae334db65c7303297d4412c6705` |
| `static/images/feed/feed-mountain-ridge-2026-07-21.png` — `exec-3bdded71-9745-4216-bd39-b3ad295a8789.png`; 1672 × 941; `77fbd11885b16511394ede4519468b2534e30c7afca8ba7b483e4e6db47b6b9c` | Replacement for legacy `mountain_walk.jpg`: simulated publish-photo fixture. | `-640.webp`: 640 × 360, 28,910 B, `4dc89816a2ae939c4a4443a51b1ceb0e9c09c6f4440ab67eeb92490de997959d`; `-1280.webp`: 1280 × 720, 88,910 B, `10f2e4975db0772caaceaabb8e848c632f74770a9e71b5814f047e6a51366717` |

## Feed-state activation audit

The six formerly weak fixture identities are live in their actual state paths:

- `?state=gallery` shows keyboard build, journal notebook, and keyboard
  components in `p-jordan-keyboard`, then prototype table, workflow closeup,
  and workflow corkboard in `p-danielle-screens`. No image path repeats across
  that rendered Gallery state.
- `?state=video` shows surf wave and the corkboard walkthrough.
- `?state=rail` shows surf wave and the same three corrected work-gallery
  identity slots.
- The simulated post flow (`Photo / video` → attach Photo → review → Publish)
  uses mountain ridge; attaching Video uses team demo, never the retired
  `team_video.jpg` fixture.

## Duplicate-image audit

All raw sources and all derivatives above have recorded SHA-256 values. The
owner-authority files are references only, never content photos. The repeated
source dHash audit (grayscale 9 × 8 dHash; Hamming distance) has closest
pairwise distance **19**; no production-content pair is at or below the
duplicate threshold of **6**. The Gallery-state regression also forbids a
repeated media path across its concurrently rendered fixtures. The six incoming
replacements and the later keyboard-components correction are versioned files
with distinct source lineage, not renamed duplicates, and retired weak legacy
filenames no longer occur in the active Feed fixture renderer.

## Exact-SHA integrated-page evidence

This document controls production-content assets; it does not treat screenshots
as product assets. The separate committed Community evidence package at
`artifacts/ps-community-tabs-001/` contains 15 real integrated-page rasters
captured from `work/2026-07-21-community-tabs-impl` at
`8326f2c3aff483f44822ae100d3dc1aedf42d437`.

`EVIDENCE_MANIFEST.json` is their authority. It records each canonical
route/state/viewport/theme/action, source-browser JFIF stream hash, true-PNG
file hash, normalized RGBA hash, exact/perceptual duplicate audit, and the
pixel-preserving JFIF-to-PNG container conversion. The older 11-file Community
evidence set was stale three-view material and was deleted rather than renamed
or used as comparison evidence. The current screenshot package contains only
Feed and The Break; no Saved-page raster is valid or retained.
