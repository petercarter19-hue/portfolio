# PeerSlate — Current State

_Verified 2026-07-18 by PS-BACKEND-NEXT-GATE-MANAGER-001. Repository facts are a snapshot; every writer must fetch `origin` before starting._

## Verified production and repository baseline

- `origin` is Azure DevOps and the only source of truth. `github` is a backup mirror whose pushes remain on hold.
- PS-RESUME-PUBLIC-REFINE-001 squash-merged through Azure PR 62 at `d88ca480a2cfcdc697d3bfffd219268c20368520`; pipeline 83 (`20260718.6`) succeeded for that exact commit.
- PS-CAPTURE-002 squash-merged through Azure PR 63 at `65c4d5a350bcaf3ea36fac55a49d14de3a7fc2fd`; pipeline 85 (`20260718.8`) succeeded for that exact commit.
- PS-MOMENT-001 squash-merged through Azure PR 66 at `43afd9353af1a0693aafab0c918f3dff92802376`; pipeline 91 (`20260718.14`) succeeded for that exact commit after both Build and Deploy passed.
- The PS-MOMENT-001 production migration and verifier passed through the configured secure connection path. They proved source pinning, two-owner isolation, deletion tombstones, explicit private confirmation, no automatic publication/placement, and full synthetic rollback without reading or printing member content.
- Production `/` and `/interview-studio` returned 200. `/app/capture`, a protected Moment review route, and the same-origin Capture-to-Moment write route all redirected a logged-out request to sign-in. No unauthenticated Moment content or mutation was exposed.
- Fetch `origin` for the exact current tip rather than treating any recorded SHA as a substitute for synchronization.
- The approved shared theme is Deep Navy Gold.

## Real and reusable — do not rebuild

- **Identity (PS-AUTH-001):** external identity, owner sessions, opaque owner IDs, and two-owner isolation.
- **Owner Settings (PS-OWNER-001 slice 1):** protected `/app/settings` and sign-out.
- **Private text Capture (PS-CAPTURE-001 + PS-CAPTURE-002):** protected create/list, revision-aware correction, archive/restore, explicit delete, and per-capture versioned export backed by owner-resolving procedures. The original text remains immutable until explicit aggregate deletion.
- **Canonical Moment (PS-MOMENT-001):** protected owner review of one pinned Capture source version, editable private proposal versions, explicit confirmation into one source-linked canonical Moment, and deterministic deleted-source tombstones. Confirmation does not publish or place content.
- **Public résumé:** canonical `/petec/resume`, existing redirects, download path, Ask Pete AI hooks, shared résumé dataset, and the refined progressive default scan.
- **Interview Studio public slice:** a public browser-local practice experience. It is not an authenticated private history system.
- **Deep Navy Gold (PS-THEME-001):** shared owner visual foundation and approved mockups under `docs/governance/approved_owner_visual_baseline/`.

## Manager and delivery lanes

ChatGPT Work is the owner-designated manager. It maintains repository truth, sequences packages, reviews handoffs, and verifies merges and releases. ChatGPT Codex owns backend convergence. Claude Code owns assigned public front-end work. Each package has one writer, one short-lived branch, and a separate file reservation.

Two lanes may proceed without sharing writable files after this manager package merges and its Azure pipeline is green:

1. **PS-PLACEMENT-001 — ChatGPT Codex:** add an explicit private reference from one confirmed Moment version to one existing owner-owned Slate destination without copying authoritative text or changing publication/audience state.
2. **PS-INTERVIEW-PUBLIC-GATE-001 — Claude Code:** continue the owner-approved Approach A design lane for the public Studio. Implementation remains gated on manager review of the returned design package.

The lanes do not share writable files. Claude Code does not create authenticated persistence; Codex does not touch public Interview Studio files. Placement is backend foundation work and does not wait for the Interview Studio design package.

## Roadmap position

| Area | Evidence state | Next gate |
|---|---|---|
| Governance and baseline | PS-MOMENT-001 release verified; manager closeout in progress | Merge this manager package before Placement starts |
| Public résumé | Refined and live through PR 62 / pipeline 83 | Preserve; no second dataset |
| Interview Studio | Public browser-local slice shipped; Approach A design approved | Fable design return, then manager implementation approval |
| Capture | Lifecycle live through PR 63 / pipeline 85 | Preserve source and revision contract |
| Canonical Moment | Live through PR 66 / pipeline 91 | Preserve confirmation, source pinning, and privacy contracts |
| Placement references | Not implemented | PS-PLACEMENT-001 after this manager gate merges |
| Journal UI | On hold | Owner must explicitly restart it |

## Honest boundaries

- No placement-reference model is implemented yet. A confirmed Moment is still private and unused by downstream surfaces until a separate explicit placement exists.
- Capture remains text-only. Voice, photo, video, and document intake wait for PS-CAPTURE-MEDIA-001/PS-VOICE-001 after the placement boundary is proven.
- Interview Studio history on the public route is browser-local demonstration state, not private account history or server persistence.
- No second résumé dataset, Journal UI, authentication rewrite, public projection, audience change, or global navigation/theme redesign is authorized in PS-PLACEMENT-001.
- The GitHub mirror is not current and must not be used as a release source.

## Required release evidence

Both guardrail suites, package-focused tests, and the Azure pipeline must pass. PS-PLACEMENT-001 additionally requires migration up/down evidence, two-owner negative authorization proof, exact confirmed-version pinning, concurrency/idempotency proof, and proof that no raw text, access grant, publication version, or downstream copy is created. A package is not “live” until its Azure squash merge is deployed and the affected production boundary is verified.
