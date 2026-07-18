# PeerSlate — Current State

_Verified 2026-07-18 by PS-NEXT-WAVE-MANAGER-001. Repository facts are a snapshot; every writer must fetch `origin` before starting._

## Verified production and repository baseline

- `origin` is Azure DevOps and the only source of truth. `github` is a backup mirror whose pushes are on hold.
- PS-RESUME-PUBLIC-REFINE-001 squash-merged through Azure PR 62 at `d88ca480a2cfcdc697d3bfffd219268c20368520`; pipeline 83 (`20260718.6`) succeeded for that exact commit.
- PS-CAPTURE-002 squash-merged through Azure PR 63 at `65c4d5a350bcaf3ea36fac55a49d14de3a7fc2fd`; pipeline 85 (`20260718.8`) succeeded for that exact commit. This is the verified application-behavior baseline before the governance-only next-wave package.
- Production `/petec/resume` returned 200 and contained the refined scan/disclosure markers. `/app/capture` and its new lifecycle/export routes enforced the sign-in boundary; same-origin negative checks rejected cross-site writes. The PS-CAPTURE-002 production migration and two-owner verification also passed without reading or printing member content.
- Fetch `origin` for the exact current tip rather than treating any recorded SHA as a substitute for synchronization.
- The approved shared theme is Deep Navy Gold.
- There were no active Azure pull requests when the audit began.

## Real and reusable — do not rebuild

- **Identity (PS-AUTH-001):** external identity, owner sessions, opaque owner IDs, and two-owner isolation.
- **Owner Settings (PS-OWNER-001 slice 1):** protected `/app/settings` and sign-out.
- **Private text Capture (PS-CAPTURE-001 + PS-CAPTURE-002):** protected create/list, revision-aware correction, archive/restore, explicit delete, and per-capture versioned export backed by owner-resolving procedures. The original text remains immutable until explicit aggregate deletion.
- **Public résumé:** canonical `/petec/resume`, existing redirects, download path, Ask Pete AI hooks, shared résumé dataset, and the refined progressive default scan.
- **Interview Studio public slice:** a public browser-local practice experience. It is not an authenticated private history system.
- **Deep Navy Gold (PS-THEME-001):** shared owner visual foundation and approved mockups under `docs/governance/approved_owner_visual_baseline/`.

## Manager and delivery lanes

ChatGPT Work is the owner-designated manager. It maintains repository truth, sequences packages, reviews handoffs, and verifies merges and releases. ChatGPT Codex owns backend convergence. Claude Code owns assigned public front-end work. Each package has one writer, one short-lived branch, and a separate file reservation.

Two packages are prepared to start in parallel after this manager package merges and its Azure pipeline is green:

1. **PS-MOMENT-001 — ChatGPT Codex:** turn one owner-scoped Capture source version into an editable private proposal and then an explicitly member-confirmed, source-linked canonical Moment.
2. **PS-INTERVIEW-PUBLIC-GATE-001 — Claude Code:** make the public demonstration, browser-local state, public-profile grounding, and future authenticated owner-workspace boundary unmistakable while progressively simplifying the public Studio experience.

The lanes do not share writable files. Claude Code does not create the authenticated owner route or persistence layer; Codex does not touch public Interview Studio files.

## Roadmap position

| Area | Evidence state | Next gate |
|---|---|---|
| Governance and baseline | Complete through PS-NEXT-WAVE-MANAGER-001 after its Azure merge | Keep records synchronized at each handoff |
| Public résumé | Refined and live through PR 62 / pipeline 83 | Preserve; no second dataset |
| Interview Studio | Public browser-local slice shipped | PS-INTERVIEW-PUBLIC-GATE-001 |
| Capture | Lifecycle live through PR 63 / pipeline 85 | Preserve source and revision contract |
| Canonical Moment | Not implemented | PS-MOMENT-001 |
| Placement references | Not implemented | Start only after Moment boundary is verified |
| Journal UI | On hold | Owner must explicitly restart it |

## Honest boundaries

- No canonical Moment or placement-reference model is implemented yet.
- Capture remains text-only. Voice, photo, video, and document intake wait for PS-CAPTURE-MEDIA-001/PS-VOICE-001 after the reviewed Moment boundary is proven.
- Interview Studio history on the public route is browser-local demonstration state, not private account history or server persistence.
- No second résumé dataset, Journal UI, authentication rewrite, placement system, or global navigation/theme redesign is authorized in the active wave.
- The GitHub mirror is not current and must not be used as a release source.

## Required release evidence

Both guardrail suites, package-focused tests, and the Azure pipeline must pass. PS-MOMENT-001 additionally requires migration up/down evidence and two-owner negative authorization proof. A package is not “live” until its Azure squash merge is deployed and the affected production boundary is verified.
