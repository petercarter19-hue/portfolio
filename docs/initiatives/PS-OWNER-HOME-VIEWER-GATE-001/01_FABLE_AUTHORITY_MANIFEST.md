# PS-OWNER-HOME-VIEWER-GATE-001 — Fable Authority Manifest

Recorded 2026-07-19 by the Claude/Fable architecture-and-feasibility writer on
branch `work/2026-07-19-owner-home-fable-architecture` (base: `origin/main`
`6d5ef46ce05bd7c3a3f6e4b4c356bdf9c9bc6fcd`). Architecture only; nothing in this
manifest is implemented, deployed, or live.

## 1. Accepted working visual direction

Pete accepted `PeerSlate-Owner-Home-Editable-Authority-Candidate-31864e4.zip`
as the **working production-intent Owner Home visual direction** on 2026-07-19.

- ZIP SHA-256: `31daf8f3d92110aed7fd540a9a20969d6084eefd59e4b94dd173db51b97575be`
- ZIP size: 16,300,454 bytes
- Contents: `visual-package-v5/` — README, 7 truth/evidence docs, 23 screens as
  editable SVG masters plus PNG review exports, the SVG design-system source
  (`design_system.mjs`, `generate_all.mjs`, `render_exports.mjs`), and one
  independently generated alpine atmosphere image.
- Preserved verbatim in this repository at
  `artifacts/ps-owner-home-viewer-gate-001/authority-candidate-31864e4/`
  (58 files). Per-file SHA-256 hashes: section 5 below.

**Owner decision, 2026-07-19 (recorded from Pete in the assignment session):**
the dark cinematic navy/gold shell, the alpine atmosphere backgrounds, and the
overall look of the accepted candidate images are to be implemented **exactly
as shown** — "make this exactly like those images we gave you, the backgrounds
and everything." Pete explicitly overrules any conflicting light-first-shell
interpretation for this surface. This closes the authority-reconciliation
question that `VISUAL_TRUTH_HANDOFF.md` left open (dark outer shell versus
light-first repository guidance): Owner Home uses the accepted dark cinematic
shell with the luminous ivory working stage, and the implementation must match
or exceed the accepted candidate under the Owner Visual Integrity Standard.
Deep Navy Gold remains the shared color system; the accepted candidate is its
authoritative expression for Owner Home. This decision does not restyle any
other released surface.

## 2. Binding baseline versus supporting references

The binding visual baseline remains:

- `docs/governance/approved_owner_visual_baseline/01_owner_home_interface_mockup.png`
  SHA-256 `c41d61758e89fc4bf2619a38f80feeec0884627f5324bfa4709f287402d67f62`
  (1,780,146 bytes)

Supporting ecosystem references (context and quality cues only — none
authorizes its product's implementation):

| Reference | Role | SHA-256 |
|---|---|---|
| `02_capturing_moments_with_peerslate.png` | Capture prominence and privacy-continuity cues | `bd843d93fc376827121c088790c23a307c71eb89e1211704eeb5cf3493f30830` |
| `03_dark_ui_concept_with_gold_accents.png` | Ecosystem / one-person-many-views context | `fb22a495c6547b1ae99f3c5b9cf8d65f7b8b7b7ba6d47fa8b8031e243176deb3` |
| `04_polished_ui_ux_storyboard_mockup.png` | Cinematic/editorial quality cues | `03ee04bbfb5e522467ff93a7542107a3a82571c04b33914a14dc13c7a5a08065` |

**Excluded:** `05_sleek_dark_ui_for_interview_practice.png`
(SHA-256 `45f9ca0edc85e9777e879e0e2224948d9cfca66bf79d49c44eba5d2d6712c2af`)
belongs exclusively to Interview Studio and must not influence Owner Home.

Authority relationship: the accepted candidate package is the working
production-intent reconstruction **of** the binding baseline. It preserves the
baseline's composition (cinematic navy shell, owner return-home feeling,
dominant upper-right Capture, luminous ivory stage, unequal editorial
hierarchy, dark insight surface, quiet relationship surface, warm next-step
surface, mobile Capture prominence) while applying the gate's truth
corrections (generic identity, honest empty states, content-free **Coming
later** capability previews, finite nine-object budget, fixture labeling).
Where the candidate and the baseline raster differ, the difference is a
recorded truth correction, not a licensed downgrade; implementation must be
recognizably both.

## 3. Truth contracts bound to this authority

The candidate package applies, and implementation must preserve, the Codex
gate contracts in this directory: `FINITE_HOME_CONTRACT.md` (nine-object
maximum, three-review maximum, deduplication, deterministic selection,
64 KiB / `private, no-store` response), `AUTHORIZATION_PROJECTION_MATRIX.md`
(authorization before retrieval; owner mode only in the first slice),
`EXPERIENCE_ACCESSIBILITY_REQUIREMENTS.md`, and `TEST_RELEASE_PLAN.md`.

This is not another visual-concept pass. No alternate visual directions may be
invented. The five audience-preview modes, Journal, My Slate, Connections,
More, Resurfaced, What PeerSlate noticed, and Connection categories appear as
polished, genuinely disabled, visibly labeled **Coming later** capability
previews exactly as composed in the candidate — with zero routes, zero
requests, and zero fabricated content.

## 4. Known-refinement register

Owner-directed implementation requirements. These refine the accepted
authority; they are not grounds to redesign or reject it.

| # | Refinement | Evidence in the accepted candidate | Owning package | Status |
|---|---|---|---|---|
| R1 | Reflow the 320px maximum-future layout so **What PeerSlate noticed** and **Your Next Useful Step** have no collisions, clipping, or cramped controls | Confirmed in export `06-owner-home-mobile-future-fixture-b-320.png`: the Noticed limitation line crowds the Inspect support / Correct / Dismiss pills, and the Next Useful Step decorative flag panel clips "Grounded in fixture review state" | `PS-HOME-FRONTEND-001` | Open — required before visual acceptance |
| R2 | Reduce repeated QA/evidence language (TEST FIXTURE / PRIVATE FIXTURE / prototype banners) in the real product interface while retaining concise truthful labels | The candidate repeats fixture/evidence pills on nearly every card; those pills are review-artifact scaffolding, not product copy. The real Home shows real owner data, so fixture pills disappear entirely; truthful state labels (Private, Coming later, Stale, etc.) remain, stated once per element | `PS-HOME-FRONTEND-001` | Open — required before visual acceptance |
| R3 | Give Recent, Resurfaced, Noticed, Connections, and Next Step more distinct decorative personalities without fabricating member content | The candidate reuses near-identical dark landscape material for Recent/Resurfaced and a generic starfield for Noticed; the baseline mockup shows distinct material per section (city Moment media area, mountain-lake resurfaced area, gold-particle insight surface, portrait-free relationship surface, warm path-and-flag next step) | `PS-HOME-FRONTEND-001` (visual assets may be prepared as package artifacts) | Open — required before visual acceptance |
| R4 | Fix the editable-package generator's Windows path handling using `fileURLToPath(import.meta.url)` and document its dependency/version | Both `generate_all.mjs` and `render_exports.mjs` used `new URL(import.meta.url).pathname`, which yields `/C:/...` percent-encoded paths on Windows and breaks `path.join`/`fs` calls; `design_system.mjs` needs no change | This architecture branch | **Done (statically):** patched copies plus dependency record at `artifacts/ps-owner-home-viewer-gate-001/windows-generator-fix/`; runtime execution not yet performed because Node.js is not installed on this workstation |

## 5. Accepted-artifact SHA-256 register

Verbatim preserved files under
`artifacts/ps-owner-home-viewer-gate-001/authority-candidate-31864e4/`:

```
716946ddcbf7b48190ab157dcdeea52a472e105d47f2675e3781b656ecdb8f72  README.md
676a26d639309f6bb755964867bc579a1b4e3d046ca89f9354ff494e55500362  assets/owner-home-alpine-atmosphere.png
993a5e4926a390d594f4f583bd5727b194760ac1b846cf108888091ed7296277  docs/01_AUTHORITY_RECONCILIATION.md
0b7484af7c1dcf5801f43f2daa2cf021758238c66c202792a897b70214586305  docs/02_TRUTH_CAPABILITY_MATRIX.md
5da864c77cdda30c925e181290d4ecef7126e30efb83c7cea53a03566c3a146b  docs/03_ACCESSIBILITY_RESPONSIVE_EVIDENCE.md
3ee31afdde174d58d06061508362f2a5e97bc5b94d8a62f004e33bb9e40e64ce  docs/04_STATE_MATRIX.md
54d02f36da30970adcdf6870537fa41cf66d4a65f5cda700c4fb746addf669c9  docs/05_COMPONENT_INVENTORY.md
159fefa98b4521a23d962ae9608fdd1202c2a376f5234df93680918e81022c95  docs/06_SCREEN_MANIFEST.md
53083017f0522b4d6dec5224275ff4874a77a9f867adbf4d2dadf8eca9fba6a4  docs/07_QA_DISPOSITION.md
bda9ba8eef1928058e56c6a3d130a4e3af4478cf6226eb9ea438af79ec00467a  exports/01-owner-home-desktop-current.png
e1c269b600d288c00592c59c64de8ac957ccf2a04dd53918ecd779787398be4b  exports/01-owner-home-desktop-current.svg
748adafc73b53cd34ead8bf90b9b83c64e9a6d9efb4976e49514037ea1a2e845  exports/02-owner-home-desktop-maximum-future-fixture-a.png
7487a3afb18e3b87032f451ccb621d0e803957c90a7801c7d24c019e23b0a526  exports/02-owner-home-desktop-maximum-future-fixture-a.svg
4f6d5198a8b07fc1b8dae33b5507f5a8f9a79de994212d16b861b31bd2b1dc68  exports/03-owner-home-mobile-current-390.png
9681b12c59456d2337ea123a513cde00049b98ea9bf308b505ef2e057d1010bb  exports/03-owner-home-mobile-current-390.svg
50d48226573e3c105637421db9d41469a7495a0a80cf6f6b3f8b22b61fefd7aa  exports/04-owner-home-mobile-future-fixture-b-390.png
69827c69550e7e44872e060287ce0f85934806c2e2cf764f798f0159c3fd7b28  exports/04-owner-home-mobile-future-fixture-b-390.svg
9f4f1fb5dbf2087825e1ff0f4ccb07a912c50c8cb5a3cc0fe07d20cc85e19925  exports/05-owner-home-mobile-current-320.png
ded2477418d72b42a5aeb3e88c10b91ccfde2ad7522910183e6f65d03f0b868a  exports/05-owner-home-mobile-current-320.svg
247168f77d403c26b9f529d4329a93feb4ccacbdfaa094b19ec7ff5a8e9d3410  exports/06-owner-home-mobile-future-fixture-b-320.png
dc3863f93c4a27dba28400c4f1a830578437604d4b710b04c3349f83ed3f90f2  exports/06-owner-home-mobile-future-fixture-b-320.svg
8e06d6440fc40f92d1d61e0ff31819a7876d2af759921bbfc0130a46c2ac0fc2  exports/07-owner-home-200-percent-reflow.png
9da165048030dc5e7a1253ddd965c55cfc39229fb6e1e1a3f8dd7c2193e56d70  exports/07-owner-home-200-percent-reflow.svg
3d897049d7140534934e64565d2f6a8c2dd32b687a72ecc740071ebed2269cab  exports/08-owner-home-long-content-fixture-b.png
ff5c4de7522c46f99989875aaa66b1af5c6e8c371f54498efe8aa266a14dcc87  exports/08-owner-home-long-content-fixture-b.svg
efb56864ad00393ea5090cf3f666b2500f75892a85bd22078dafb8f7aa4717b6  exports/09-owner-home-visible-focus.png
a9c11d05a178f27a9b30165ee1f8b72e92fe2df3f1aaa7ab284acaf4e660cd1f  exports/09-owner-home-visible-focus.svg
4ab83033b40f0bdccabe92a1ff8238a5a725139fb9e3fa55abdc810da4f1011d  exports/10-owner-home-high-contrast.png
8326c19235267d7d83a8bd384f2d48085d012088053d798d914fa5e389abb79a  exports/10-owner-home-high-contrast.svg
1deaca7383c86d212fca7175cf0a825c9fc796ca3290518af83580d95cf69eeb  exports/11-owner-home-reduced-motion.png
c4e7e60ae32324547a810d67266fd6af1ccfba12122b63332909beede4f679a6  exports/11-owner-home-reduced-motion.svg
b6fc3c711ae8fe30dd8f7e97e7acfda6ef33e27c16129e975d80ef567caebded  exports/12-owner-home-loading.png
fd00848628c80cd460d8e5fac923593e7ecf5224adb593be531838ea26305b1c  exports/12-owner-home-loading.svg
53098d89546bb6122f004605c8adc475c31ac1bd159050f5c5e6a00f669fd656  exports/13-owner-home-empty.png
973603728728426ee7b3c49cde532e833f99ba850ed01158b6aa724caf4186a0  exports/13-owner-home-empty.svg
c35b1bb71423481658f3b416552e8ebc7b6ee18e521105830a8e8a13ad655b93  exports/14-owner-home-partial-failure.png
4e73e4f93acbaa8099fa58378ada2287572f90dfad4d3a7b4378c12541350b61  exports/14-owner-home-partial-failure.svg
c8dc0bb244b8ed87c6843a835736cc34a1789d91e75009fe2e67839b7fd37c89  exports/15-owner-home-complete-failure.png
2557a298fcbed6dc0d10e1ac5911ce069f5d6dd9d1cdd9009e54f791ca5ce005  exports/15-owner-home-complete-failure.svg
b25df2514e7986f83b388f8354093fa8d6e3207bc4393f27b057bb06189a37c9  exports/16-owner-home-stale.png
66af3a7227c39917149f6515562221e2e286b74bcd6814476b2c43722b4dc446  exports/16-owner-home-stale.svg
09821b123d3b4237408703aa39b551850bcd2f7bb2f1803785f2024dd758d999  exports/17-owner-home-restricted.png
c5fefecac23bca1d9292e33bab37a5e532e9a4c5b3b140e4cb3e358992e1857a  exports/17-owner-home-restricted.svg
c3a29819a96369a87f54db2794422f30fa44e6138a10b4992c1bd2265af04243  exports/18-owner-home-recovery.png
ab313b5cde9894b6f5093742f3efad923d3dd01221920de7112f2302cf894b78  exports/18-owner-home-recovery.svg
f00564552f86d29d48b1a44f7bf1a760e89386150111936e792bc6469fa31956  exports/19-owner-home-finite-nine-object-evidence.png
0ff9160ada152369a10ac871d95ca67929494f822cef8315d945bbf0413406a6  exports/19-owner-home-finite-nine-object-evidence.svg
745db3a7f5023d297798ea1369ee2eb04784d35bda7015ec366106c67d5cc5a9  exports/20-owner-home-authority-comparison.png
82c1ae0e2228d32516dd2f4b02c0d0fe0a4d352bbe84e7f103ec76eff7e394e2  exports/20-owner-home-authority-comparison.svg
776215887b9c08be796022ef93c6be2f39e44c43c3fd466048d3f5231c1fce85  exports/21-owner-home-status-and-homepage-impact.png
9c038f27a81c04b6addf8cfa7317e2d59caeead069e0322dce3b9d2a8a60485e  exports/21-owner-home-status-and-homepage-impact.svg
5c4a106ad4d04962d9114c235a282512370416851ca4a2513da65db870841267  exports/22-owner-home-access-lifecycle-evidence.png
4a5b1baffb242346c4bafc219c999e9b9ef2272aa690730599cf3256ce3f27e2  exports/22-owner-home-access-lifecycle-evidence.svg
0fb5639ee49caace823f38245fd6481c4ea20b6d6f612cdfde69b23c124de0ad  exports/23-owner-home-orientation-landscape-current-844.png
81d37cc77f9a492e7a1474d615ce941b9ca075e49b58ec8eb32d30c91957e203  exports/23-owner-home-orientation-landscape-current-844.svg
f1af14cc9f588acbe429aba6fc4f0a972de14558bc0735d06337d443c5aba874  source/design_system.mjs
dea1c367d683347706e2a99888a0655c38c81ea27ee1d90378b1d90983aeaf5b  source/generate_all.mjs
4b04061f553dd22011b4ed8f6f909dd020bcc4126693d2e4acd944ef51306084  source/render_exports.mjs
```

The two patched generator files under
`artifacts/ps-owner-home-viewer-gate-001/windows-generator-fix/` intentionally
differ from `source/generate_all.mjs` and `source/render_exports.mjs` by
exactly the documented `fileURLToPath` correction (see `GENERATOR_NOTES.md`
there). They are a recorded correction, not part of the accepted original.

## 6. Status labels

- Accepted candidate: **working production-intent visual direction** (Pete,
  2026-07-19). Final V3 visual acceptance still occurs against the real
  implemented product, per `OWNER_VISUAL_INTEGRITY_STANDARD.md`.
- This manifest: architecture record only. Owner Home is **not implemented,
  not deployed, and not live**.
