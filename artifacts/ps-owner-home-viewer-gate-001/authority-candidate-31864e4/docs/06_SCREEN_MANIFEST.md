# Screen manifest

Every row has an editable SVG and a matching PNG review export.

| # | Screen | Size |
|---:|---|---:|
| 01 | Desktop current capability | 1440×1100 |
| 02 | Desktop maximum future fixture A | 1440×1100 |
| 03 | Mobile current | 390×2228 |
| 04 | Mobile future fixture B | 390×2684 |
| 05 | Mobile current | 320×2296 |
| 06 | Mobile future fixture B | 320×2708 |
| 07 | 200% structured reflow | 1024×2640 |
| 08 | Long-content, bidi, and missing-media fixture | 1440×1240 |
| 09 | Visible focus | 1440×1100 |
| 10 | High contrast / forced-colors direction | 1440×960 |
| 11 | Reduced motion | 1440×960 |
| 12 | Loading | 1440×960 |
| 13 | Empty | 1440×1100 |
| 14 | Partial failure | 1440×960 |
| 15 | Complete failure | 1440×960 |
| 16 | Stale concurrency | 1440×960 |
| 17 | Restricted | 1440×960 |
| 18 | Recovery: retry succeeds and retry fails | 1440×960 |
| 19 | Exact nine-object proof | 1440×960 |
| 20 | Binding-authority side-by-side comparison | 1920×1180 |
| 21 | Claim boundary and homepage impact | 1440×900 |
| 22 | Access and lifecycle evidence | 1440×1080 |
| 23 | Standalone landscape-width current reflow | 844×2228 |

## Reproduction

From the package root:

```bash
node source/generate_all.mjs
node source/render_exports.mjs
```

The renderer uses the locally available Sharp dependency to convert SVG masters into review PNGs. Regeneration does not fetch production data or call any application service.
