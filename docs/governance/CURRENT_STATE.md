# PeerSlate - Current State

_Updated 2026-07-19 for the completed Voice release, Interview Studio Image 5
5A-light/5C-dark authority, and Capture Media manager planning. Every manager
and writer must still fetch `origin` before starting._

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
- Portable session management, the Codex Interview Gate 2.4 review contract,
  and Claude Co-Work Capture Media manager planning squash-merged through Azure
  PR 78 at `c4e5145026cc9a67a68c6c147cc5daa8db386f7a`; pipeline 110 passed Build
  and Deploy for that exact commit. A redundant manual pipeline 111 for the
  same commit was canceled after pipeline 110 succeeded; it was not a failed
  release. Production `/`, `/petec/resume`, `/interview-studio`, and
  `/petec/my-story` returned 200; `/my-story` kept its canonical redirect; and
  `/app/capture` kept its signed-out redirect to sign-in.
- The protected Voice visual-parity correction was accepted by Pete and
  ChatGPT Work at V3 after Claude Code relinquished exact tip
  `e32b31d7c351ac2f8601a4467bcd1c9450f52c3b`. Azure PR 80 squash-merged the
  accepted package at `864a79d1bc1fc61e62f2d2a544dd54a01ebdcb82`;
  pipeline 113 (`20260719.21`) passed Build and Deploy for that exact commit.
  Production `/` and `/feed-living-stream?state=voice` returned 200;
  `/app/capture` returned the expected signed-out 302 to sign-in; and the live
  Voice CSS/JavaScript served the accepted gold Save, dynamic modal semantics,
  focus/background controls, and Voice-scoped asset signatures. The available
  verification browser had no signed-in member session, so this closeout does
  not claim a new post-deploy authenticated screenshot or repeat the already
  completed real Speech workflow.
- Voice governance closeout PR 81 squash-merged at
  `5cc5b69346ee354bcc36248f7ee5724ce13c9d08`; pipeline 115
  (`20260719.23`) passed Build and Deploy for that exact commit. Production
  `/`, `/interview-studio`, and `/feed-living-stream?state=voice` returned 200,
  and `/app/capture` kept the expected signed-out redirect to sign-in.
- The real-Studio-first homepage-demo convergence package squash-merged through
  Azure PR 83 at `cee015f6291fe5460a6a5d5795c445bb6b25c6f9` after the
  clean implementation tip
  `9ea02196f6410fbbe40aa60355f6013815a7e625`. Pipeline 117
  (`20260719.25`) passed Build and Deploy for that exact merge. A redundant
  manual run 118 for the same SHA was canceled after the automatic run was
  identified; it is not a failed release. Live `/`, `/interview-studio`, and
  `/interview-studio/history` returned 200, and `/app/capture` kept the expected
  signed-out redirect. This governance-only release changed no Studio or demo
  website behavior.
- Fetch `origin` for the exact current tip rather than treating any recorded SHA as a substitute for synchronization.
- The approved shared theme is Deep Navy Gold.

## Real and reusable - do not rebuild

- **Identity (PS-AUTH-001):** external identity, owner sessions, opaque owner IDs, and two-owner isolation.
- **Owner Settings (PS-OWNER-001 slice 1):** protected `/app/settings` and sign-out.
- **Private text Capture (PS-CAPTURE-001 + PS-CAPTURE-002):** protected create/list, revision-aware correction, archive/restore, explicit delete, and per-capture versioned export backed by owner-resolving procedures. The original text remains immutable until explicit aggregate deletion.
- **Private Voice Capture (PS-VOICE-001):** protected Speak/Type entry, private
  original audio, managed-identity Speech transcription, editable transcript,
  explicit private save, playback/download, retry, lifecycle/export/delete,
  and the accepted walkthrough-level desktop/mobile experience. Future
  destinations and attachments remain disabled `Coming later` scaffolding.
- **Canonical Moment (PS-MOMENT-001):** protected owner review of one pinned Capture source version, editable private proposal versions, explicit confirmation into one source-linked canonical Moment, and deterministic deleted-source tombstones. Confirmation does not publish or place content.
- **Private Placement reference (PS-PLACEMENT-001):** an explicit, owner-scoped, lifecycle-aware pointer from one exact confirmed Moment version to one existing eligible private/unpublished Slate destination. The reference copies no authoritative text and changes no audience, access grant, publication record, destination content, or downstream room.
- **Public resume:** canonical `/petec/resume`, existing redirects, download path, Ask Pete AI hooks, shared resume dataset, and the refined progressive default scan.
- **Interview Studio public slice:** a public browser-local practice experience. It is not an authenticated private history system.
- **Deep Navy Gold (PS-THEME-001):** shared owner visual foundation and approved mockups under `docs/governance/approved_owner_visual_baseline/`.

## Manager and delivery lanes

The task manager is a package-designated role. ChatGPT Work/Codex manager
sessions and Claude Co-Work have the same governed manager authority when an
active initiative names them. A manager maintains repository truth, sequences
the assigned package, reserves shared files, defines visual authority, records
manager acceptance, and coordinates Azure closeout. Codex and Claude writers
self-manage their assigned branches through implementation, complete-diff
review, correction, tests, evidence, PR readiness, and post-acceptance release.
The designated manager may rely on a coherent `Pass` self-certification instead
of repeating the complete technical audit.

Each package has one designated manager and one active writer per branch.
Claude Co-Work management is distinct from Claude Code implementation. Parallel
manager sessions may coordinate separate packages, but shared-governance-file
reservations must be serialized.

The Interview Studio review lane and Capture Media manager-planning lane are
active independently. The Voice correction lane is closed:

1. **PS-INTERVIEW-PUBLIC-GATE-001 - Gate 2.4 review:** the exact Image 5
   authority is recorded: Concept A Editorial Studio Ledger controls
   default/light and Concept C Cinematic Studio controls optional dark. A new
   Codex manager session may receive the complete dual-theme nine-screen design
   package, review it on a clean design-review branch, and return a `Pass`,
   `Conditional`, or `Fail` report to Claude Co-Work. It does not implement the
   Studio.
2. **Interview homepage demo - parked dependent prototype:** Claude's clean
   pushed `work/2026-07-19-home-interview-demo-001` checkpoint was observed at
   `358e7eea304a2b4d4008031ea8f51c523380ee4f`. Its modal, static-state,
   accessibility, responsive, and no-JavaScript work is reusable, but its
   paper-light dark treatment and Voice-first framing predate the controlling
   5A/5C and written-practice decisions. It is not accepted, merged, deployed,
   or live. Hold it until the real Studio is accepted, implemented, released,
   and verified live; then converge it in a separate demo closeout.
3. **PS-CAPTURE-MEDIA-001 - manager planning:** Claude Co-Work is the designated
   session manager for requirements, architecture, decomposition, and writer
   allocation. No authoritative Azure implementation branch was observed at
   activation, so Capture Media is not implemented, deployed, or live.

The completed Voice lane preserves its original worktrees as historical
references. They are not active writing lanes and must not be reused for later
Voice changes. The released code and evidence on `origin/main` are authority.

The completed Placement foundation does not depend on Interview Studio. Voice Capture also does not authorize a placement UI or downstream Story/Work/Project/resume/Studio/Journal/Feed consumer.

## Roadmap position

| Area | Evidence state | Next gate |
|---|---|---|
| Governance and baseline | Bible v2.5, Roadmap v2.4, visual-integrity enforcement, Story composition authority, self-managed writers, and portable package managers are current | Use self-certified lane reports plus focused Pete/designated-manager acceptance; serialize shared-governance updates |
| Public resume | Refined and live through PR 62 / pipeline 83 | Preserve; no second dataset |
| Interview Studio | Public browser-local slice shipped; Approach A approved; Image 5 Concept A controls default/light and Concept C controls optional dark for the same public Studio; homepage demo is a parked prototype only | Complete dual-theme Gate 2.4 and feasibility/approval; architecture and implement the real Studio; release and verify it live; then converge and separately release the homepage demo |
| Capture | Text lifecycle and private Voice Capture are deployed; Pete verified the signed-in workflow; Pete and ChatGPT Work accepted the corrected responsive visuals; PR 80 / pipeline 113 released them | Preserve the released privacy, lifecycle, Speak/Type, and visual contracts; any refinement is a new package |
| Capture Media | Manager planning active under Claude Co-Work; no implementation branch or release evidence is authoritative yet | Define photo/video/document vertical slices, shared private-media/provenance/lifecycle contracts, first writer, and exact entry gate |
| Canonical Moment | Live through PR 66 / pipeline 91 | Preserve confirmation, source pinning, and privacy contracts |
| Placement references | Backend foundation live through PR 68 / pipeline 93 | Add UI or downstream consumption only through a separately approved package |
| My Story composition | Current public Pete Story is a fixed fixture-driven projection; member editing is not live | Preserve PS-STORY-COMPOSER-001 as planned future work until its full design, schema, authorization, accessibility, and publication entry gate is approved |
| Journal UI | On hold | Owner must explicitly restart it |

## Honest boundaries

- The Placement reference model is live, but no website control creates or displays placements yet. Existing Moments and destinations remain unchanged until a future authorized consumer explicitly invokes the stored-procedure boundary.
- Voice is functionally deployed, visually accepted, and closed through PR 80 /
  pipeline 113. The live protected route still requires sign-in; the closeout's
  post-deploy evidence proves the production asset signatures and auth boundary,
  not a new authenticated screenshot or a repeated real Speech transaction.
- Production has the required private Blob Storage and managed-identity Blob and
  Speech roles. The active correction must not change those backend contracts.
- PS-CAPTURE-MEDIA-001 planning does not make photo, video, or document Capture
  available. Voice is not to be rebuilt inside the broader media package.
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
  visual comparison evidence and Pete plus designated-session-manager visual
  acceptance.
- The homepage Voice walkthrough is the minimum for the real protected Voice
  Capture UI, with Speak and Type as first-class choices.
- The approved future Community, Connections, selected-audience, Story, Slate
  Board, résumé, attachment, AI-draft, and publication affordances may appear as
  polished, explicitly disabled `Coming later` scaffolding. Only private Capture
  save is live; frontend capability state is never authorization.
- Interview Studio Image 5 Concept A controls default/light and Concept C
  controls optional dark. They are two themes of the same public Studio, not
  separate products. Theme switching may not reset Studio state. Implementation
  remains blocked until the complete dual-theme Gate 2.4 design set,
  truth/accessibility review, Claude/Fable feasibility, and Pete/manager visual
  approval pass.
- The homepage Interview walkthrough is downstream of the real Studio. Its
  current branch is a prototype, not a release. It must remain static and
  no-side-effect, but its light/dark composition, written-practice hierarchy,
  product labels, truth, and mapped states must converge on the exact accepted
  and live Studio before it can receive separate visual acceptance and release.
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

Both guardrail suites, package-focused tests, and the Azure pipeline must pass
for every later package. PS-VOICE-001 has already proved owner-isolated private
Blob authorization, managed-identity Speech access, transcription review before
save, source deletion/export behavior, and text fallback; later packages must
preserve those released contracts.

For material user-facing packages, the release evidence must also include the
named visual authority, desktop/mobile and applicable focus/zoom/reduced-motion/
failure comparisons, recorded deviations, and explicit Pete/designated-manager
visual acceptance.
