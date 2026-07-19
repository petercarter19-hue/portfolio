# PeerSlate - Current State

_Updated 2026-07-19 for the released Voice implementation, owner functional validation, reopened Voice visual gate, and self-managed delivery decision. Every writer must still fetch `origin` before starting._

## Verified production and repository baseline

- `origin` is Azure DevOps and the only source of truth. `github` is a backup mirror whose pushes remain on hold.
- PS-RESUME-PUBLIC-REFINE-001 squash-merged through Azure PR 62 at `d88ca480a2cfcdc697d3bfffd219268c20368520`; pipeline 83 (`20260718.6`) succeeded for that exact commit.
- PS-CAPTURE-002 squash-merged through Azure PR 63 at `65c4d5a350bcaf3ea36fac55a49d14de3a7fc2fd`; pipeline 85 (`20260718.8`) succeeded for that exact commit.
- PS-MOMENT-001 squash-merged through Azure PR 66 at `43afd9353af1a0693aafab0c918f3dff92802376`; pipeline 91 (`20260718.14`) succeeded for that exact commit after both Build and Deploy passed.
- The PS-MOMENT-001 production migration and verifier passed through the configured secure connection path. They proved source pinning, two-owner isolation, deletion tombstones, explicit private confirmation, no automatic publication/placement, and full synthetic rollback without reading or printing member content.
- PS-PLACEMENT-001 squash-merged through Azure PR 68 at `e0462a2e4683c91ebe518b6d984a2a8b973ba3d5`; pipeline 93 (`20260719.1`) succeeded for that exact commit after both Build and Deploy passed.
- The PS-PLACEMENT-001 production migration and verifier passed through the configured secure connection path. They proved exact confirmed-version pinning, two-owner isolation, destination eligibility, explicit remove/reactivate lifecycle, zero content copy, no access/publication/downstream writes, and full synthetic rollback without reading or printing member content.
- Production `/`, `/petec/resume`, and `/interview-studio` returned 200. `/app/capture` and a protected Moment review route redirected logged-out requests to sign-in. No unauthenticated private content or mutation was exposed.
- The governance closeout for Placement squash-merged through Azure PR 69 at `d11163cd1753e47aa12f139166b6af71069f2d81`; pipeline 95 (`20260719.3`) passed Build and Deploy.
- The Voice activation package squash-merged through Azure PR 70 at `5488819ad13d3f411319d7e184fde3779d62b8d2`; manually queued pipeline 97 passed Build and Deploy. It authorized and specified PS-VOICE-001 without changing website behavior.
- Bible v2.4, the Owner Visual Integrity Standard, and the durable manager
  handoff squash-merged through Azure PR 71 at
  `28ec01097677219bbe466ff2c731707d0e4a2b89`; pipeline 99
  (`20260719.7`) passed Build and Deploy. The governance-only release changed no
  website behavior. After an App Service restart/warm-up, `/`, `/petec/resume`,
  and `/interview-studio` returned 200 and `/app/capture` redirected to sign-in.
- Bible v2.5, Roadmap v2.4, and the member-directed Story composition contract
  squash-merged through Azure PR 73 at
  `aaee6e563a94e19d1786ded3f636d8376e20d500`; pipeline 102
  (`20260719.10`) passed Build and Deploy. The governance-only release changed
  no website behavior. Production `/`, `/petec/resume`, `/interview-studio`,
  and `/petec/my-story` returned 200; `/my-story` kept its canonical redirect;
  and `/app/capture` kept its signed-out redirect to sign-in.
- PS-VOICE-001 squash-merged through Azure PR 75 at
  `eede8565d703a466bd788962d494e8b385b53409`; pipeline 105 passed Build and
  Deploy for that exact commit. Production Storage/RBAC and SQL migration
  verification passed, and Pete completed the signed-in Voice workflow and
  confirmed that it functions.
- Pete then withdrew Voice visual acceptance: the protected desktop and mobile
  interface is materially flatter and clunkier than the approved homepage/feed
  walkthrough. The release remains technically deployed but product/visual
  status is In Progress until Claude's corrective visual-parity package passes.
- The self-managed delivery model and Claude Voice correction allocation
  squash-merged through Azure PR 76 at
  `fe03d49ca57bde2c4d0bfc4c66726c132da81ebf`; pipeline 107 passed Build and
  Deploy for that exact commit. Public route behavior remained unchanged.
- Fetch `origin` for the exact current tip rather than treating any recorded SHA as a substitute for synchronization.
- The approved shared theme is Deep Navy Gold.

## Real and reusable - do not rebuild

- **Identity (PS-AUTH-001):** external identity, owner sessions, opaque owner IDs, and two-owner isolation.
- **Owner Settings (PS-OWNER-001 slice 1):** protected `/app/settings` and sign-out.
- **Private text Capture (PS-CAPTURE-001 + PS-CAPTURE-002):** protected create/list, revision-aware correction, archive/restore, explicit delete, and per-capture versioned export backed by owner-resolving procedures. The original text remains immutable until explicit aggregate deletion.
- **Canonical Moment (PS-MOMENT-001):** protected owner review of one pinned Capture source version, editable private proposal versions, explicit confirmation into one source-linked canonical Moment, and deterministic deleted-source tombstones. Confirmation does not publish or place content.
- **Private Placement reference (PS-PLACEMENT-001):** an explicit, owner-scoped, lifecycle-aware pointer from one exact confirmed Moment version to one existing eligible private/unpublished Slate destination. The reference copies no authoritative text and changes no audience, access grant, publication record, destination content, or downstream room.
- **Public resume:** canonical `/petec/resume`, existing redirects, download path, Ask Pete AI hooks, shared resume dataset, and the refined progressive default scan.
- **Interview Studio public slice:** a public browser-local practice experience. It is not an authenticated private history system.
- **Deep Navy Gold (PS-THEME-001):** shared owner visual foundation and approved mockups under `docs/governance/approved_owner_visual_baseline/`.

## Manager and delivery lanes

ChatGPT Work is the owner-designated task manager and final acceptance room. It
maintains repository truth, sequences packages, reserves shared files, defines
visual authority, and records final product acceptance. Codex and Claude
self-manage their assigned branches: implementation, complete-diff review,
correction, tests, evidence, PR readiness, and post-acceptance Azure
release/closeout. ChatGPT Work may rely on a coherent `Pass` self-certification
instead of repeating the complete technical audit. Each package still has one
writer, one short-lived branch, and explicit file ownership.

The Interview Studio design lane and protected Voice visual-correction lane are active independently:

1. **PS-INTERVIEW-PUBLIC-GATE-001 - public design:** continue the owner-approved Approach A visual-design lane for the public Studio. Implementation remains gated on manager and owner approval of the returned visual package.
2. **PS-VOICE-001 - protected visual correction:** the backend, infrastructure,
   SQL, merge, deploy, and signed-in functional path are real. Claude Code now
   owns the self-managed desktop/mobile visual-parity correction on a fresh
   branch from current `origin/main`; the original Codex worktree remains
   preserved and must not be reused.

The Claude branch `work/2026-07-19-voice-visual-parity-001` was observed at
`0158daf22d26e7c38be494e2b32e6b51fdaca0fb` with design instructions only. The
manager-approved implementation answers now live in the PS-VOICE-001 visual
correction addendum. Claude must synchronize with current `origin/main`; no
implementation or acceptance is inferred from that planning checkpoint.

The completed Placement foundation does not depend on Interview Studio. Voice Capture also does not authorize a placement UI or downstream Story/Work/Project/resume/Studio/Journal/Feed consumer.

## Roadmap position

| Area | Evidence state | Next gate |
|---|---|---|
| Governance and baseline | Bible v2.5, Roadmap v2.4, visual-integrity enforcement, Story composition authority, and self-managed lanes are current | Use self-certified lane reports plus focused Pete/ChatGPT Work acceptance; keep Story Composer planned |
| Public resume | Refined and live through PR 62 / pipeline 83 | Preserve; no second dataset |
| Interview Studio | Public browser-local slice shipped; Approach A approved; Direction A art direction selected | Complete the nine-screen Gate 2.4 package, Claude/Fable feasibility review, then Pete/manager visual approval before implementation |
| Capture | Text lifecycle and private Voice Capture are deployed; Pete verified the signed-in Voice workflow works | Rebuild protected Voice desktop/mobile visuals to match the approved walkthrough, then obtain final product acceptance |
| Canonical Moment | Live through PR 66 / pipeline 91 | Preserve confirmation, source pinning, and privacy contracts |
| Placement references | Backend foundation live through PR 68 / pipeline 93 | Add UI or downstream consumption only through a separately approved package |
| My Story composition | Current public Pete Story is a fixed fixture-driven projection; member editing is not live | Preserve PS-STORY-COMPOSER-001 as planned future work until its full design, schema, authorization, accessibility, and publication entry gate is approved |
| Journal UI | On hold | Owner must explicitly restart it |

## Honest boundaries

- The Placement reference model is live, but no website control creates or displays placements yet. Existing Moments and destinations remain unchanged until a future authorized consumer explicitly invokes the stored-procedure boundary.
- Voice is functionally deployed, but it is not visually accepted or closed.
  Working behavior and successful deployment do not override the reopened visual
  gate.
- Production has the required private Blob Storage and managed-identity Blob and
  Speech roles. The active correction must not change those backend contracts.
- Interview Studio history on the public route is browser-local demonstration state, not private account history or server persistence.
- No second resume dataset, Journal UI, authentication rewrite, public projection, audience change, placement UI, downstream consumer, or global navigation/theme redesign is authorized by PS-VOICE-001.
- The GitHub mirror is not current and must not be used as a release source.
- The current public My Story separates fixture content from repository-authored
  layout metadata, but a signed-in member cannot yet move, resize, save, or
  publish a personal composition. `PS-STORY-COMPOSER-001` is planned, not live.

## Owner visual-integrity decision

- Bible v2.5 and `OWNER_VISUAL_INTEGRITY_STANDARD.md` make selected
  production-intent demonstrations binding visual minimums. The real experience
  must be recognizable as the approved demonstration and match or exceed it.
- Functional, privacy, security, accessibility, test, pipeline, and production
  evidence remain required. Material user-facing work also requires named
  visual comparison evidence and Pete plus ChatGPT Work visual acceptance.
- The homepage Voice walkthrough is the minimum for the real protected Voice
  Capture UI, with Speak and Type as first-class choices.
- The approved future Community, Connections, selected-audience, Story, Slate
  Board, résumé, attachment, AI-draft, and publication affordances may appear as
  polished, explicitly disabled `Coming later` scaffolding. Only private Capture
  save is live; frontend capability state is never authorization.
- Direction A is selected for Interview Studio, but implementation remains
  blocked until the complete Gate 2.4 design set and visual reviews pass.
- The current homepage overall is not an approved final visual baseline; its
  broader redesign remains a separate later initiative.

## Owner Story composition decision

- Bible v2.5, Roadmap v2.4, and
  `OWNER_STORY_COMPOSITION_STANDARD.md` make Story composition member-directed.
- The future authenticated editor must let a member move and resize supported
  notes, text, images, and media; control overlap/layering; use keyboard and
  structured alternatives; preview responsive/audience states; save a private
  layout draft; and publish separately.
- AI may propose an arrangement but may not silently apply, overwrite, save, or
  publish it. Layout metadata remains separate from canonical Story content.
- Pete's first acceptance case is the **I went back at 36** card: he must be able
  to shrink or move it so it no longer obscures the sailboat in the Maui image.
- This decision does not modify the current public Story or start the future
  implementation package.

## Required release evidence

Both guardrail suites, package-focused tests, and the Azure pipeline must pass for every later package. PS-VOICE-001 must additionally prove owner-isolated private Blob authorization, managed-identity Speech access, transcription review before save, full source deletion/export behavior, and text fallback before Voice Capture may be called live.

For material user-facing packages, the release evidence must also include the
named visual authority, desktop/mobile and applicable focus/zoom/reduced-motion/
failure comparisons, recorded deviations, and explicit Pete/ChatGPT Work visual
acceptance.
