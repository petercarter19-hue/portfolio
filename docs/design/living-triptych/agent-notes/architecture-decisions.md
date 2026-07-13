# Living Triptych — Architecture Decision Record (shared)

Shared between Codex and Claude Code. During isolated experimentation each agent
may propose here with an author tag; entries are ratified once branches are
reconciled. Format: ADR-NNN, status, decision, rationale, author.

---

### ADR-001 — Route & nav placement for the experimental Overview
- **Status:** Adopted (Claude branch)
- **Decision:** New experience lives at its own route **`/atrium`** with a dedicated header link **"Atrium"** (leftmost in `.platform-nav__links`). It does **not** replace `/` or `/petec`. `/atrium` opts out of the `profile_tabs` sub-nav to stay full-bleed.
- **Rationale:** It is a "big swing that might not land" (Pete). A separate link lets it be judged live against the current homepage; if it lands it can become the front door, if not it retires without collateral. "Atrium" names the rotunda the slabs stand in and reads distinct from "Overview." (Named with Pete.)
- **Author:** Claude

### ADR-002 — Build on Foundation A tokens, server-rendered
- **Status:** Proposed (Claude)
- **Decision:** Slice 1 is server-rendered Jinja extending `base.html`, with `design-system/tokens.css` loaded in `extra_head`, a dedicated `static/css/atrium.css`, and a small vanilla `static/js/atrium.js`. Reuse `.ps-glass-card` vocabulary + `sky-glass` backdrop.
- **Rationale:** Matches repository reality (Flask + Jinja + hand-written CSS + vanilla JS, no bundler). Keeps the Atrium on the approved design system without restyling other pages.
- **Author:** Claude

### ADR-003 — Data-driven slab view model (tenant-safe)
- **Status:** Proposed (Claude)
- **Decision:** The three slabs render from a generic view model (Story / Projects / Résumé dimensions), not hardcoded Pete strings. Pete's `resume_data.json` + `story_data.json` populate the demo; `living_resume_fixtures.json` proves it works for other personas.
- **Rationale:** AGENTS.md — components must work for students → senior users; never hardcode employers/dates/metrics. Pete is fixture data.
- **Author:** Claude

### ADR-004 — Rendering technology for the slabs
- **Status:** Open — decided by the `atrium-arrival-exploration` workflow (CSS-3D vs CSS+SVG vs WebGL-hybrid) + Codex's parallel exploration.
- **Leaning:** DOM/CSS(+SVG for curved edge-light) for slice 1; **WebGL/Three.js deferred** to a later, evidence-gated milestone (no-build Flask site; loading/fallback/maintainability cost). To be confirmed against working evidence, not argument.
- **Author:** Claude (pending)

### ADR-005 — Content authenticity guardrails
- **Status:** Adopted (repo rule)
- **Decision:** No fictional résumé data, **no MICAP**, no retired résumé example in any visible Atrium copy. Real Northrop/L3Harris/USAF chapters + non-MICAP metrics only.
- **Author:** Claude (per AGENTS.md)
