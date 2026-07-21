# PeerSlate - Current State

_Reconciled 2026-07-21 by `PS-GOV-TRUTH-RECONCILIATION-001`. Azure PRs 103-110,
112-114, 116, 117, and 119 were completed, deployed, and green but had never
been recorded here; PR 111 and PR 118 were the only merges in the 103-119 range
that this file acknowledged. The homepage Interview parity lane was also
recorded as open after it had been implemented, released, closed out, and
verified live. Both are corrected below. The reconciliation changes governance
records only and makes no new live claim._

_Updated 2026-07-20 for the released flag-off Photo experience, released
default-off Owner Home backend, released/live-verified 5A-light/5C-dark
Interview Studio, the exact-authority Owner Home frontend activation, and the
owner-authorized one-Journal system architecture. Bible v2.8 and Roadmap v2.7
are the current universal-Capture, Journal, return-value, AI, and future
messaging authority.
Every manager and writer must still fetch `origin` before starting._

## Verified production and repository baseline

- `origin` is Azure DevOps and the only source of truth. `github` is a public
  backup mirror whose pushes remain on hold pending explicit owner approval.
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
- Pete accepted the current fixed homepage Interview walkthrough for its
  illustrative purpose. Claude's clean pushed source tip
  `90d035a25344c850e6ed732c1efb6e4d0a240787` squash-merged through Azure PR 86
  at `a98cced519a1f853ad9f4462fd438efa67d6f260`. Automatic pipeline 122
  (`20260719.30`) passed Build and Deploy for that exact merge. Automatic
  pipeline 123 (`20260719.31`) then passed for descendant main
  `6cb49f135cc3a2749dd4539f8261d176b43dad9a`, whose demo-owned paths are
  byte-for-byte unchanged from the PR 86 merge. Manual pipeline 124
  (`20260719.32`) also passed for that same descendant SHA; it was redundant
  successful evidence, not proof of a CI-trigger failure.
- Live `https://peerslate.com/`,
  `/static/css/homepage-scenes.css?v=interview-demo-1`, and
  `/static/js/homepage-interview-demo.js?v=int-demo-1` returned 200. The live
  DOM contains the poster, modal dialog, four fixed states, truth markers, and
  final `/interview-studio` link. Manager browser review passed the desktop
  flow and 390px reflow without page-level horizontal overflow. This is a
  released demonstration, not final 5A/5C homepage parity.
- The Photo 1 member experience was accepted for a flag-off release at source
  `a19a5034aa7f3b9d355f8862aa98a34eb9f3e5f6`. Azure PR 98 squash-merged it at
  `e5912c85d95dddbaed9c565d1e599efe2c8dd0b6`; automatic pipeline 143
  (`20260720.14`) passed Build and Deploy. Live public routes stayed healthy,
  `/app/capture` retained its signed-out redirect, the Photo asset returned 200,
  and the Photo mutation route returned neutral 404 with the flag off. Photo is
  not enabled; signed-in lifecycle, two-owner, homepage-parity, and enablement
  gates remain open.
- The finite Owner Home backend passed at source
  `efd19d820986a529d48e2fcf660655b9f4dfc492`. Azure PR 99 squash-merged it at
  `2db2ca5c93fa221f7092b54ebc17f2068584c07d`; automatic pipeline 145
  (`20260720.16`) passed Build and Deploy. The passwordless production SQL
  migration and outer-rollback verifier passed. The feature flag remains off,
  `/app` is unchanged, and `/api/v1/owner/home` returns neutral 404. Queued
  duplicate manual pipeline 146 was canceled and is not a failed release.
- Pete delegated the current ChatGPT Work/Codex manager to complete the needed
  review, corrections, and release. The final source
  `0aaf41768a33810b089f5fea3a66a5272e8b61d8` passed 68 Interview tests, 104
  combined package/governance tests, 599 full-suite tests with two unrelated
  isolated-SQL skips, clean JavaScript parsing, diff checks, and desktop/390px
  browser verification. Azure PR 101 squash-merged it at
  `39002f5130a1766d2090007c16582e0dbe07226c`; automatic pipeline 149
  (`20260720.20`) passed Build and Deploy. Live `/interview-studio` and
  `/interview-studio/history` serve the accepted product, the three versioned
  Interview/theme assets hash byte-for-byte to the release, and modal theme
  controls retain dialog state and focus with zero console errors. The source
  branch is deleted and the implementation/release lane is closed.
- Interview release-governance PR 102 squash-merged at
  `2e811f4eec3e915bdb6a0aefa7bd744d6bc7553b`; automatic pipeline 150
  (`20260720.21`) passed Build and Deploy. It changed governance only and
  formally closed the release lane.
- The connected-system candidate package merged through Azure PR 111 at
  `938d2b8b3b4450b1f1e4d0796aa6b5b438e0e5ed`; pipeline 162
  (`20260720.33`) passed. Peter then supplied the owner-approved CURRENT/LOCKED
  Bible v2.7 and Roadmap v2.6 artifacts. This activation promotes their exact
  repository candidate lineage into the controlled governance set. It changes
  no application, route, schema, feature flag, deployment configuration, or
  member-facing behavior.
- The July 20 one-Journal authority replaces the candidate connected-system
  assumptions that required a Capture destination, a draft-to-Journal
  promotion, or a separately authored Journal-entry body. Bible v2.8, Roadmap
  v2.7, `PS-GOV-JOURNAL-SYSTEM-001`, the controlling `PS-JOURNAL-001`
  architecture, `PS-RETURN-VALUE-001`, `PS-ASK-SLATE-AI-001`,
  `PS-MESSAGING-001`, and the legal/model-routing standards are governance and
  implementation authority. Source
  `578081f5191dd74daa154941604a2b199c5fed58` squash-merged through Azure PR
  118 at `3d7c9e10811dcbcc763d965d7770bd0d35e51d4b`; automatic pipeline 171
  (`20260721.1`) passed Build and Deploy. Delayed run-list visibility caused a
  redundant manual pipeline 172 (`20260721.2`), which also passed and is not a
  second release claim. Production `/` and the actual direct App Service host
  returned 200; `/app` and `/app/capture` retained their signed-out 302
  boundaries; `/journal` remained 404. This release changes no current route,
  schema, feature flag, application behavior, or member-facing capability.
- **Previously unrecorded releases, reconciled 2026-07-21.** Each of the
  following completed through an Azure squash-merge pull request with a
  successful automatic Build and Deploy pipeline. They were verified against the
  Azure pull-request and pipeline records on 2026-07-21.

  | PR | Merge commit | Pipeline | What it released |
  |---|---|---|---|
  | 103 | `b7b674415f1f7c9ac2844fa0482091b62a7ec979` | 151 | Homepage Interview parity architecture activation (governance only) |
  | 104 | `5217247d811d81af6ca92504dda62d9a2c756563` | 153 | Exact-authority Owner Home frontend activation (governance only) |
  | 105 | `4deb0a07b6faf2d93d445e212207aeb84b1a71c4` | 154 | **PS-HOME-INTERVIEW-PARITY-001 implementation** from source `6625b52ca4620b503ec56dcc15567470b6ef2499` |
  | 106 | `8fb501da2405d30b76613902648ac1eb0232c058` | 156 | Homepage Interview parity release governance closeout |
  | 107 | `531013dd8c1a05e2443becd881a226755f27ca14` | 157 | Capture Photo production lifecycle proof definition |
  | 108 | `919adba534d70c4f3f30979b8d43e000912079c8` | 158 | **Photo lifecycle dark-launch gate implementation** from source `f74afcea11f74b8be1b8034d98080c0c5cc38b32` |
  | 109 | `df8b1872740435f2baeddc204f130202ab73e87e` | 160 | Photo lifecycle gate release closeout |
  | 110 | `1fb64380186447c0512b4a1b277ff6d0a6f3d767` | 161 | Next-task board and connected-system handoff staging |
  | 112 | `ef918e05421e9a8d048018f0f9fd71549ea822fc` | 163 | Branch, worktree, and stash disposition record |
  | 113 | `45f4a338a838fa013aea08e3f2bc4e3641abee83` | 164 | PS-INTERVIEW-HISTORY-SALVAGE-001 salvage analysis package (analysis delivered; **three blocking questions in `06_OPEN_QUESTIONS_FOR_PETE.md` remain unanswered**, so the package is not closed and no writer may be named) |
  | 114 | `ed3409a902f38e9437f6fbf70d3f2f61625037f4` | 165 | **Interview coaching failure diagnostics** in `app.py` |
  | 116 | `2bf989e074e274520558a9f3674e5c3f426c3d63` | 167 | Journal restart as the memory profile |
  | 117 | `efd34335284d6c823d47cd7bac3cd2f901533612` | 169 | Bible v2.7 and Roadmap v2.6 authority activation |
  | 119 | `0717e03c9f1d4e6b67f355fd1556651086ddc351` | 173 | Journal system authority release-evidence closeout |

  Azure **PR 115 was abandoned**, not merged. It attempted the same v2.7/v2.6
  activation that PR 117 completed; its unmerged source branch
  `work/2026-07-20-bible-v27-activation` is still on `origin` and is an archive
  candidate.

  The baseline previously recorded `journal_restart_pipeline: 168`, which is the
  redundant manual run for merge `2bf989e`. The automatic CI run for that merge
  was pipeline 167. Both passed; 167 is the release run.

- **PS-HOME-INTERVIEW-PARITY-001 is complete and homepage Interview parity is
  closed.** The package progressed from architecture checkpoint
  `353a5810b18e7db22f35319fbecc9c2fa97d8b72` through manager-required
  corrections to implementation source
  `6625b52ca4620b503ec56dcc15567470b6ef2499`. Azure PR 105 squash-merged it at
  `4deb0a07b6faf2d93d445e212207aeb84b1a71c4`; automatic pipeline 154
  (`20260720.25`) passed Build and Deploy. PR 106 / pipeline 156 closed its
  release governance. Its completion report records `Pass` self-certification
  and "Complete, released, and verified live". On 2026-07-21 live
  `https://peerslate.com/` served `homepage-scenes.css?v=interview-parity-1` and
  `homepage-interview-demo.js?v=int-parity-1`, matching `templates/homepage.html`
  on `main`. Written `Interview Me` is primary, light is Editorial Studio
  Ledger, and dark is Cinematic Studio rather than the previous paper-white
  modal.
- **PS-CAPTURE-PHOTO-LIFECYCLE-001 is complete.** PR 107 / pipeline 157 defined
  the production lifecycle proof, PR 108 / pipeline 158 implemented the
  server-only dark-launch gate with `services/photo_lifecycle_access_service.py`
  and its tests, and PR 109 / pipeline 160 closed the release. Photo remains
  flag-off; no member-facing Photo capability is live. The package records
  **Defender choice B** — no production EICAR or malware test, production
  malicious path stays Conditional.
- **Current deployed tip and current application behavior are different
  commits.** Pipeline 173 deployed `main` at
  `0717e03c9f1d4e6b67f355fd1556651086ddc351`. The most recent commit that
  changed shipped application code is `ed3409a902f38e9437f6fbf70d3f2f61625037f4`
  (PR 114, pipeline 165, Interview coaching diagnostics in `app.py`); the most
  recent change to shipped templates or static assets is
  `4deb0a07b6faf2d93d445e212207aeb84b1a71c4` (PR 105, pipeline 154). Everything
  merged after PR 114 was documentation or package-local tooling. The baseline
  previously pinned application behavior to `39002f5` / pipeline 149, which had
  been superseded twice.
- **Four pushed branches sit outside every lane record.** They are unmerged, not
  abandoned, and named in no initiative:
  `work/2026-07-20-interview-me-microphone-001`,
  `work/2026-07-20-interview-validator-truthfulness-001`,
  `work/2026-07-20-photo-proof-readiness-001`, and
  `work/2026-07-20-bible-v27-activation`. See
  `docs/governance/OPEN_BRANCH_REGISTER.md`. The photo-proof branch records that
  the owner replaced Defender choice B with choice A; `main` still records B, so
  **B remains controlling until Pete confirms otherwise** and no production
  Defender test is authorized by that unmerged branch.
- **2026-07-21 release wave.** Five further merges landed the same day. Verified
  against the Azure pull-request and pipeline records and against production.

  | PR | Merge commit | Pipeline | What it released |
  |---|---|---|---|
  | 121 | `6496d3f8747fb5e2bbfeaf06fc43ac3f52480ac6` | 174 | PS-JOURNAL-001 visual handoff material for a ChatGPT first screen set (separate active lane) |
  | 122 | `6cd8cffb46841e896f0458a1a8e371d9c59626c1` | 176 | That handoff's closeout |
  | 123 | `f3749d86c308ab0884882bdaff71c2543f4e8a8a` | 177 | **Repair of the two live Interview Studio 502 defects** |
  | 124 | `6d36bd48c9fff97d7dcb1a00ebed36e55c5d658b` | 178 | **Continuous speak-your-answer dictation**; asset signature `studio-5a5c-4` |
  | 125 | `74a7427e775d3b49df839fbecc1ffa20c545c471` | 179 | Photo proof-window readiness; Defender A/B contradiction resolved; Photo still flag-off |

  Redundant manual run 180 was queued for the same tip after run 179 was slow to
  appear in the run list; 179 is the release run and 180 is not a second release
  claim. This repeats the delayed automatic-run visibility already recorded for
  pipelines 171/172.

  **Post-release production verification, 2026-07-21.** `/` 200,
  `/interview-studio` 200, `/interview-studio/history` 200, `/app` 302,
  `/app/capture` 302, `/journal` 404, and `POST /app/capture/photo` a neutral
  404 with the Photo flag still off. Live `/interview-studio` serves
  `interview-studio.js?v=studio-5a5c-4`, and that file carries both the PR 123
  validator repair and the PR 124 dictation implementation.

- **A second writer was active during this reconciliation.** PRs 121 and 122 came
  from `work/2026-07-21-journal-visual-handoff` and its closeout while
  `PS-GOV-TRUTH-RECONCILIATION-001` held the shared-governance reservation. That
  lane touched only `docs/initiatives/PS-JOURNAL-001/**`, so nothing contended,
  but the reconciliation began from a stated assumption of a single active
  session and that assumption was wrong. A manager must verify concurrency by
  fetching `origin` rather than relying on it being asserted.
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
- **Public Ask Pete AI:** a real typed visitor assistant at `POST /api/chat`
  grounded in approved public Markdown knowledge. It currently has a
  1,000-character text boundary and no voice, attachment, OCR, private
  owner-history retrieval, or saved job-analysis workspace.
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

The Interview Studio writer-release, homepage Interview parity, Photo lifecycle
dark-launch, Owner Home backend, and Voice correction lanes are all closed.
Capture Media Photo enablement remains open under its separate gate. Owner Home
frontend is manager-activated with a Codex frontend task assigned as sole
writer; as of 2026-07-21 no home-frontend writer branch exists on `origin`, so
that lane is activated but not started. `PS-GOV-TRUTH-RECONCILIATION-001` is the
only currently in-progress lane and is governance-only:

1. **PS-INTERVIEW-PUBLIC-GATE-001 - released and verified live:** the exact
   Image 5 Concept A default/light and Concept C optional dark implementation
   is live through source `0aaf41768a33810b089f5fea3a66a5272e8b61d8`, Azure
   PR 101, merge `39002f5130a1766d2090007c16582e0dbe07226c`, and automatic
   pipeline 149. The implementation/release branch was deleted.
2. **PS-HOME-INTERVIEW-PARITY-001 - complete, released, and verified live
   (corrected 2026-07-21):** the paragraph below describes the lane as it stood
   before PR 105. It is retained as lineage. The lane is now closed: activation
   PR 103 / pipeline 151, implementation PR 105 / pipeline 154 from source
   `6625b52ca4620b503ec56dcc15567470b6ef2499` at merge
   `4deb0a07b6faf2d93d445e212207aeb84b1a71c4`, closeout PR 106 / pipeline 156.
   Homepage Interview parity is closed and no writer remains assigned. Its
   pre-release history follows. The
   `PS-HOME-INTERVIEW-DEMO-001` walkthrough was implemented and accepted for its
   fixed illustrative purpose, deployed, and live through source
   `90d035a25344c850e6ed732c1efb6e4d0a240787`, Azure PR 86, merge
   `a98cced519a1f853ad9f4462fd438efa67d6f260`, and automatic pipeline 122.
   Its modal, static-state, accessibility, responsive, and no-JavaScript work
   is real. Its paper-light dark treatment and Voice-default framing still
   predate the controlling 5A/5C and written-practice decisions. The real
   Studio release gate is now satisfied. The current ChatGPT Work/Codex manager
   assigned Claude Code to write the convergence architecture and then
   implement on fresh branch `work/2026-07-20-home-interview-parity-001` from
   exact post-activation `origin/main`. The clean pushed architecture checkpoint
   was `353a5810b18e7db22f35319fbecc9c2fa97d8b72`. That review completed, the
   manager-required corrections were applied, and implementation, acceptance,
   Azure release, and live proof all followed through PRs 105 and 106.
3. **PS-CAPTURE-MEDIA-001 - Photo released flag-off; enablement gates open:**
   the backend, foundation, and accepted Photo 1 experience are deployed through
   PRs 95, 96, and 98 with successful pipelines 139, 140, and 143. Nothing new
   is member-visible while the flag remains off. A new assignment is required
   for real signed-in lifecycle, two-owner denial, homepage parity, and any
   enablement decision.
4. **PS-HOME-BACKEND-001 complete / PS-HOME-FRONTEND-001 activated:** the finite
   backend and production SQL are released through PR 99 at
   `2db2ca5c93fa221f7092b54ebc17f2068584c07d` with pipeline 145. The feature
   remains off and `/app` is unchanged. After the governance-only activation
   release and green pipeline, the separately assigned Codex writer creates
   `work/2026-07-20-home-frontend-001` from that exact `origin/main` and owns
   only the accepted finite frontend surface. The first release consumes the
   existing `owner-home.v1` contract without backend expansion or fabricated
   client state. Empty, populated, complete-unavailable, actual retry/recovery,
   flag-off fallback, and truthful `coming_later` availability are runtime
   evidence. Partial-failure, stale/`409`, and restricted runtime states remain
   deferred design authority until a separate backend-contract package can
   represent them. Broader viewer modes remain inactive, and Owner Home stays
   default-off until a later explicit enablement decision.

`PS-ASK-PETE-AI-001` is the public Ask Pete / reusable Ask [Name] AI package.
Its real typed public slice remains live; future work may refine only the
public-audience experience and approved public grounding. Signed-in private
history, Type/Speak/file/screenshot workflows, and member-action proposals now
belong to planned `PS-ASK-SLATE-AI-001`. Neither planned package has an assigned
manager, writer, implementation branch, start date, deployment, or new live
claim.

`PS-PROJECTS-001` is separately planned under Roadmap Phase 10. It defines a
private-first Project Workspace that connects exact governed records without
copying canonical facts, plus separately gated purpose- and audience-specific
Project Projections. It has no active manager, writer, implementation branch,
schema migration, accepted production-intent mockup, deployment, or live claim.
The direction package and controlled Bible v2.6/Roadmap v2.5 baseline were
released through Azure PR 91 at squash merge
`bb6fa7057d12537a4076b4c8dfd7ce1e0cf77d90`; pipeline 131 passed Build and
Deploy for that exact commit. Live `/projects`, `/petec/projects`, `/work`, and
`/petec/work` still redirect to `/petec/resume#experience`, as intended.

The completed Voice lane preserves its original worktrees as historical
references. They are not active writing lanes and must not be reused for later
Voice changes. The released code and evidence on `origin/main` are authority.

The completed Placement foundation does not depend on Interview Studio. Voice Capture also does not authorize a placement UI or downstream Story/Work/Project/resume/Studio/Journal/Feed consumer.

## Roadmap position

| Area | Evidence state | Next gate |
|---|---|---|
| Governance and baseline | Bible v2.8, Roadmap v2.7, one-Journal and trusted-return authority, visual-integrity enforcement, Story composition and Projects system authority, early legal readiness, self-managed writers, and portable package managers are current | Use one durable manager, one self-managed writer, and risk-based independent review; serialize shared-governance updates |
| Public resume | Refined and live through PR 62 / pipeline 83 | Preserve; no second dataset |
| Interview Studio | Exact 5A-light/5C-dark product is released and verified live through source `0aaf41768a33810b089f5fea3a66a5272e8b61d8`, PR 101, merge `39002f5130a1766d2090007c16582e0dbe07226c`, and pipeline 149; the converged homepage walkthrough is released and live through PR 105/pipeline 154 and closed out by PR 106/pipeline 156, superseding the PR 86/pipeline 122 pre-convergence demonstration | Homepage Interview parity is **closed**; any further Interview change requires a new package and a fresh homepage-impact assessment |
| Capture | Text lifecycle and private Voice Capture are deployed; Pete verified the signed-in workflow; Pete and ChatGPT Work accepted the corrected responsive visuals; PR 80 / pipeline 113 released them | Preserve the released privacy, lifecycle, Speak/Type, and visual contracts; any refinement is a new package |
| Capture Media | Photo backend plus accepted Photo 1 experience released flag-off through PRs 95/96/98 and pipelines 139/140/143; the server-only lifecycle dark-launch gate released through PRs 107/108/109 and pipelines 157/158/160 with Defender choice B recorded; no Photo intake is member-visible | Keep Photo off; settle the Defender choice A/B contradiction in the open-branch register; then assign the remaining isolation, homepage parity, and enablement gates |
| Owner Home | Dark cinematic authority accepted; finite backend and production SQL released default-off through PR 99/pipeline 145; `/app` unchanged and API neutral 404; exact-authority frontend activation released through PR 104/pipeline 153 | The activation is released. No `work/2026-07-20-home-frontend-001` branch exists on `origin` as of 2026-07-21, so the assigned Codex writer has not started. Create it from current `origin/main` and implement only truthful `owner-home.v1` states; keep broader viewer modes separate |
| Canonical Moment | Live through PR 66 / pipeline 91 | Preserve confirmation, source pinning, and privacy contracts |
| Placement references | Backend foundation live through PR 68 / pipeline 93 | Add UI or downstream consumption only through a separately approved package |
| Ask Pete / Ask [Name] AI | Public typed Ask Pete is live against approved public knowledge; no private Slate access or uploads are live | Preserve the public-only boundary and later generalize only through a separately accepted public package |
| Ask Slate AI | Signed-in member-intelligence umbrella is architecture only; Ask My Slate is a contextual CTA and specialist workflows are not separate bots | Sequence after private Journal and authorization foundations; gate private multimodal inputs, proposals, retention, and source display independently |
| Homepage product projections | Cross-product parity governance is active; Interview Studio parity closed through PR 105/pipeline 154; Voice parity closed through PR 80/pipeline 113; Capture Photo homepage parity remains open and gated behind Photo enablement | Every material user-facing package assesses `/`; update affected sections in the same wave or activate an exact downstream parity package and keep parity open until accepted and live |
| My Story composition | Current public Pete Story is a fixed fixture-driven projection; member editing is not live | Preserve PS-STORY-COMPOSER-001 as planned future work until its full design, schema, authorization, accessibility, and publication entry gate is approved |
| Projects | Historical public Project material and redirects exist; no authenticated canonical Projects product is live | Preserve PS-PROJECTS-001 as planned Phase 10 work; validate Project/Work/Slate Board boundaries and approve a private-workspace visual authority before implementation |
| Journal system | Controlling architecture is complete; Capture is an action, Save Moment is the single member commit, and owner-Journal membership is derived from eligible private canonical Moments; no target Journal UI is live | Assign one writer to the private-core entry gate and prove route/data/auth/lifecycle/visual/accessibility/migration/rollback/two-member behavior |
| Return value | Replay/resurfacing, Momentum, Prompt/Ritual, What PeerSlate Noticed, and Slate Mirror have committed staged architecture only | Begin only after the private Journal core; keep every output private, source-linked, dismissible, correctable, non-diagnostic, and non-shaming |
| Messaging | Consent- and safety-gated future architecture only | Require identity, Connection/consent, authorization, moderation, retention/deletion, notification, abuse, and legal gates before implementation |

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
- Owner Home architecture acceptance and backend activation do not make Owner
  Home available. `/app` remains the released owner workspace until a separate
  frontend package is accepted, merged, deployed, and explicitly enabled.
- Ask Pete AI's typed public slice is live, but a document or job-posting
  screenshot cannot currently be uploaded there; voice and private Slate
  grounding are not live there. Those private capabilities are planned under
  Ask Slate AI, not Ask Pete. Uploaded targets must never be inferred to be
  public, indexed, recommended, or part of a job marketplace.
- PS-PROJECTS-001 is a planned direction package only. No canonical Project
  aggregate, Project Workspace, Project Projection, Project collaboration,
  Project task management, or new public Project route is implemented or live.
  Slate Board Project notes and historical fixtures are not canonical Projects.
- **Two Interview Studio defects found and fixed on 2026-07-21.** Both were live
  in production when found. Both are now repaired, released, and verified live
  through Azure PR 123 at `f3749d86c308ab0884882bdaff71c2543f4e8a8a`, automatic
  pipeline 177 (`20260721.7`). Live
  `https://peerslate.com/static/js/interview-studio.js` carries the fix. They are
  recorded here because they were live and undetected, not because they remain
  open.

  **(a) Interview Me coaching fails on honest empty output.**
  `validate_interview_review` rejects a review whose `strengths` list is empty,
  but the coaching prompt sets a maximum of four bullets and never a minimum, so
  a genuinely weak answer can legitimately produce zero strengths. Isolated
  against the suite's own `valid_review()` fixture: with strengths the review
  passes the summary check; with `strengths: []` and nothing else changed it is
  rejected as `review summary is incomplete` and the request returns 502. This
  is intermittent and strikes precisely the weak answers a struggling member
  submits. Azure PR 114 (pipeline 165) added coaching failure diagnostics to
  attribute exactly this class of 502 and named "a reply carrying an empty
  strengths array" as one cause; the repair for that cause was left on an
  unmerged branch.

  **(b) "Get Answer" in `best_practice` and `compare` modes cannot succeed.** The
  best-practice system prompt instructs the model to return `"evidenceIds":[]`,
  but `validate_interview_model_answer` rejects an empty list, and the call
  supplies an empty evidence map so any cited id is rejected as unauthorized.
  Both possible outputs fail, so every such request returns 502. Verified by
  calling the validator directly against `main` at
  `0717e03c9f1d4e6b67f355fd1556651086ddc351`. The fix is built and reviewed on
  Grounded `member_history` model answers were unaffected by (b).

  Both were repaired by the same change: `strengths` is no longer required while
  `improvements` still is, and `validate_interview_model_answer` gained
  `require_evidence`, applied only to illustrative best-practice answers. Both
  security properties were re-verified after the fix: an illustrative answer that
  cites any id is still rejected, and a grounded answer with no citation is still
  rejected.
- Interview Studio history on the public route is browser-local demonstration state, not private account history or server persistence.
- Bible v2.8 and Roadmap v2.7 activate the one-Journal architecture only. No
  target Journal route, public/Connection projection, replay/resurfacing,
  Momentum, Prompt/Ritual, What PeerSlate Noticed, Slate Mirror, Ask Slate AI,
  or messaging runtime is live. Legacy `/api/journal/*` endpoints are
  prompt/response implementation history, not proof of the one Journal.
- The currently deployed Capture page and Capture-to-Moment review mechanics
  remain real implementation history and must be preserved until an approved
  migration replaces their presentation. They do not lock Capture as a future
  navigation destination, require an Add to Journal step, or authorize copied
  Journal content. The future member-facing commit is Save Moment; derived
  Journal membership and downstream reference projections still require a new
  implementation package.
- `PS-RETURN-VALUE-001`, `PS-ASK-SLATE-AI-001`, and `PS-MESSAGING-001` are
  committed planned architectures, not active implementations. Slate Spine,
  Backstory Drawer, Studio Return Ticket, Then and Now, Focus Theme, Progress
  Keepsake, Life Constellation, synthetic own-voice playback, and remaining
  research options are preserved in the Revisit Register, not promised for the
  first release.
- No second resume dataset, Journal UI, authentication rewrite, public projection, audience change, placement UI, downstream consumer, or global navigation/theme redesign is authorized by PS-VOICE-001.
- The GitHub mirror is not current and must not be used as a release source;
  it is public, so advancing it requires explicit owner approval.
- The current public My Story separates fixture content from repository-authored
  layout metadata, but a signed-in member cannot yet move, resize, save, or
  publish a personal composition. `PS-STORY-COMPOSER-001` is planned, not live.

## Owner visual-integrity decision

- Bible v2.8 and `OWNER_VISUAL_INTEGRITY_STANDARD.md` make selected
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
  separate products. Theme switching may not reset Studio state. The complete
  dual-theme Gate 2.4 set, truth/accessibility review, Claude/Fable feasibility,
  implementation, and owner-delegated manager visual approval culminated in
  source `0aaf41768a33810b089f5fea3a66a5272e8b61d8`, PR 101, live merge
  `39002f5130a1766d2090007c16582e0dbe07226c`, and pipeline 149. Azure release
  and live verification have passed.
- The homepage Interview walkthrough is downstream of the real Studio. Its
  current fixed, fictional, no-side-effect version is accepted and live as a
  pre-convergence demonstration, but it is not final visual parity. Its
  light/dark composition, written-practice hierarchy, product labels, truth,
  and mapped states must converge on the exact accepted and live Studio under
  active `PS-HOME-INTERVIEW-PARITY-001` before homepage parity can close. The
  live Voice-default copy and paper-light dark modal are known downstream work,
  not the real Studio's controlling visual or product authority.
- Every current and future homepage product section now follows the same
  cross-product projection contract. A material real-product change triggers a
  homepage-impact assessment and either a same-wave accepted update or an exact
  downstream parity package. The real product is upstream authority; homepage
  parity remains open while the public section is stale. Voice and Interview
  Studio are current examples, not exceptions limited to those two products.
- The current homepage overall is not an approved final visual baseline; its
  broader redesign remains a separate later initiative.

## Owner Story composition decision

- Bible v2.8, Roadmap v2.7, and
  `OWNER_STORY_COMPOSITION_STANDARD.md` make Story composition member-directed.
- Journal and My Story remain architecturally distinct views over shared exact
  Moment references. The owner Journal is complete, chronological, searchable,
  and lifecycle-oriented; a public Journal is a curated timeline/profile
  projection; My Story is a finite, intentionally selected and visually
  composed narrative. Saving a Moment adds nothing to Story, removing a Story
  item does not remove it from Journal, and neither view owns a second fact body.
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


## PS-COMMUNITY-TABS-001 (added 2026-07-21)

Active, implementation not yet merged. Community will land on Feed with a
seamless Studio-style switch to The Break and a Saved tab; People & Interests
retires with URLs redirecting. Nothing user-visible has changed for this
package yet; the sample-community honesty labels remain in force throughout.
