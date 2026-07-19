# PeerSlate — Current State

_Verified 2026-07-18 by PS-PLACEMENT-RELEASE-MANAGER-001. Repository facts are a snapshot; every writer must fetch `origin` before starting._

## Verified production and repository baseline

- `origin` is Azure DevOps and the only source of truth. `github` is a backup mirror whose pushes remain on hold.
- PS-RESUME-PUBLIC-REFINE-001 squash-merged through Azure PR 62 at `d88ca480a2cfcdc697d3bfffd219268c20368520`; pipeline 83 (`20260718.6`) succeeded for that exact commit.
- PS-CAPTURE-002 squash-merged through Azure PR 63 at `65c4d5a350bcaf3ea36fac55a49d14de3a7fc2fd`; pipeline 85 (`20260718.8`) succeeded for that exact commit.
- PS-MOMENT-001 squash-merged through Azure PR 66 at `43afd9353af1a0693aafab0c918f3dff92802376`; pipeline 91 (`20260718.14`) succeeded for that exact commit after both Build and Deploy passed.
- The PS-MOMENT-001 production migration and verifier passed through the configured secure connection path. They proved source pinning, two-owner isolation, deletion tombstones, explicit private confirmation, no automatic publication/placement, and full synthetic rollback without reading or printing member content.
- PS-PLACEMENT-001 squash-merged through Azure PR 68 at `e0462a2e4683c91ebe518b6d984a2a8b973ba3d5`; pipeline 93 (`20260719.1`) succeeded for that exact commit after both Build and Deploy passed.
- The PS-PLACEMENT-001 production migration and verifier passed through the configured secure connection path. They proved exact confirmed-version pinning, two-owner isolation, destination eligibility, explicit remove/reactivate lifecycle, zero content copy, no access/publication/downstream writes, and full synthetic rollback without reading or printing member content.
- Production `/`, `/petec/resume`, and `/interview-studio` returned 200. `/app/capture` and a protected Moment review route redirected logged-out requests to sign-in. No unauthenticated private content or mutation was exposed.
- Fetch `origin` for the exact current tip rather than treating any recorded SHA as a substitute for synchronization.
- The approved shared theme is Deep Navy Gold.

## Real and reusable — do not rebuild

- **Identity (PS-AUTH-001):** external identity, owner sessions, opaque owner IDs, and two-owner isolation.
- **Owner Settings (PS-OWNER-001 slice 1):** protected `/app/settings` and sign-out.
- **Private text Capture (PS-CAPTURE-001 + PS-CAPTURE-002):** protected create/list, revision-aware correction, archive/restore, explicit delete, and per-capture versioned export backed by owner-resolving procedures. The original text remains immutable until explicit aggregate deletion.
- **Canonical Moment (PS-MOMENT-001):** protected owner review of one pinned Capture source version, editable private proposal versions, explicit confirmation into one source-linked canonical Moment, and deterministic deleted-source tombstones. Confirmation does not publish or place content.
- **Private Placement reference (PS-PLACEMENT-001):** an explicit, owner-scoped, lifecycle-aware pointer from one exact confirmed Moment version to one existing eligible private/unpublished Slate destination. The reference copies no authoritative text and changes no audience, access grant, publication record, destination content, or downstream room.
- **Public résumé:** canonical `/petec/resume`, existing redirects, download path, Ask Pete AI hooks, shared résumé dataset, and the refined progressive default scan.
- **Interview Studio public slice:** a public browser-local practice experience. It is not an authenticated private history system.
- **Deep Navy Gold (PS-THEME-001):** shared owner visual foundation and approved mockups under `docs/governance/approved_owner_visual_baseline/`.

## Manager and delivery lanes

ChatGPT Work is the owner-designated manager. It maintains repository truth, sequences packages, reviews handoffs, and verifies merges and releases. ChatGPT Codex owns backend convergence. Claude Code owns assigned public front-end work. Each package has one writer, one short-lived branch, and a separate file reservation.

The public design lane may continue. The backend lane has completed Placement and waits for Pete's next package decision:

1. **PS-INTERVIEW-PUBLIC-GATE-001 — public design:** continue the owner-approved Approach A visual-design lane for the public Studio. Implementation remains gated on manager and owner approval of the returned visual package.
2. **Backend convergence — waiting:** do not start a new Codex package until Pete chooses voice/non-text Capture or owner Home/viewer-mode work.

The completed Placement foundation does not depend on Interview Studio. It also does not authorize a placement UI or downstream Story/Work/Project/résumé/Studio/Journal/Feed consumer.

## Roadmap position

| Area | Evidence state | Next gate |
|---|---|---|
| Governance and baseline | PS-PLACEMENT-001 release verified | Keep current pointers synchronized at the next owner decision |
| Public résumé | Refined and live through PR 62 / pipeline 83 | Preserve; no second dataset |
| Interview Studio | Public browser-local slice shipped; Approach A and functional design blueprint approved | ChatGPT Pro visual directions, Claude feasibility review, then manager/owner implementation approval |
| Capture | Lifecycle live through PR 63 / pipeline 85 | Preserve source and revision contract |
| Canonical Moment | Live through PR 66 / pipeline 91 | Preserve confirmation, source pinning, and privacy contracts |
| Placement references | Backend foundation live through PR 68 / pipeline 93 | Add UI or downstream consumption only through a separately approved package |
| Journal UI | On hold | Owner must explicitly restart it |

## Honest boundaries

- The Placement reference model is live, but no website control creates or displays placements yet. Existing Moments and destinations remain unchanged until a future authorized consumer explicitly invokes the stored-procedure boundary.
- Capture remains text-only. Voice, photo, video, and document intake wait for PS-CAPTURE-MEDIA-001/PS-VOICE-001 after the placement boundary is proven.
- Interview Studio history on the public route is browser-local demonstration state, not private account history or server persistence.
- No second résumé dataset, Journal UI, authentication rewrite, public projection, audience change, placement UI, downstream consumer, or global navigation/theme redesign was added by PS-PLACEMENT-001.
- The GitHub mirror is not current and must not be used as a release source.

## Required release evidence

Both guardrail suites, package-focused tests, and the Azure pipeline must pass for every later package. Any placement consumer must independently prove owner/viewer authorization, explicit member action, no canonical-text fork, no implicit publication/audience change, and lifecycle/revocation behavior before it is called live.
