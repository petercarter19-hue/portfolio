# Living Triptych — Visual & Technical Comparison (shared)

Side-by-side of the Codex and Claude Arrival prototypes, so the strongest pieces
of each can be combined (per the collaboration model: the winner may be Codex's
component structure + Claude's motion + Codex's responsive + Claude's a11y, etc.).

_Populate once both prototypes render. Attach screenshots under this folder._

| Dimension | Codex prototype | Claude prototype |
|---|---|---|
| Route / entry | _tbd_ | `/atrium` (link: "Atrium", leftmost) |
| Rendering tech | _tbd_ | DOM/CSS `preserve-3d` triptych, no new deps (exploration Approach 1, score 84) |
| Architectural feel (curved/edge-lit) | | Gradient cylindrical shading + edge-light rail; **SVG barrel silhouette pending** (next milestone) |
| Overlap readability | | AA — opaque indigo centre occludes cleanly; wings keep content in outer two-thirds; identity scrim |
| Real content inside slabs | | Story photos + values, Projects pillars, Résumé real chapters + `$36M+`/`7 platforms` — all from fixtures |
| Accessibility (kbd, focus, reduced-motion, forced-colors, 200%) | | One h1 + 3 labelled slabs, real Enter links, `:focus-within` lift, reduced-motion + forced-colors fallbacks |
| Responsive (desktop 3D / tablet / mobile reinterpretation) | | Desktop fan → tablet reduced depth → mobile cinematic vertical stack |
| Performance (backdrop-filter budget, load) | | 3 blurred slabs + sky; no JS needed for content; entrance is pure CSS |
| Maintainability / Flask fit | | server-rendered Jinja + `--ps-*` tokens + per-experience CSS + view model |
| Fidelity to mockup (0–100) | | ~72 for slice 1 (curvature is the main gap; SVG silhouette would lift it) |

## Screenshots
- Claude: captured live at 1366×820 (desktop triptych) and 375×812 (mobile stack) on `127.0.0.1:5057/atrium` — see session. Save to this folder before cross-review.
- Codex: _pending_

## Synthesis recommendation (combine the strongest)
_TBD after cross-review._
