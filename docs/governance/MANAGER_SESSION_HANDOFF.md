# PeerSlate Manager Session Handoff

_Prepared 2026-07-18 and updated 2026-07-19 after the completed Voice visual
release, with Interview Gate 2.4 review and Capture Media planning still active.
Repository and branch facts are a snapshot; fetch `origin` before acting._

## Start here on any computer

1. Open the authoritative Azure clone and follow root `START_HERE.md` exactly.
2. Fetch `origin`, inspect the current branch/worktree, and fast-forward a clean
   `main`. Never disturb a dirty task worktree to make it current.
3. Read `CURRENT_BASELINE.yaml`, `CURRENT_STATE.md`,
   `ACTIVE_INITIATIVES.md`, this handoff, the current Bible/Roadmap, and the
   assigned initiative.
4. Treat the merged repository as authority. Chat memory, downloaded ZIPs,
   local worktrees, and this dated snapshot do not replace current `origin/main`.

## Manager role and lane model

- **Designated session manager:** a package-specific role that may be held by a
  ChatGPT Work/Codex manager session or Claude Co-Work. Both have the same
  sequencing, governance, file-boundary, visual-authority, exception,
  acceptance, and Azure-closeout authority when assigned.
- **ChatGPT Codex:** may be a bounded manager/reviewer session or a self-managed
  implementation writer; the assigned initiative must say which role applies.
- **Claude Co-Work:** currently receives the Interview Gate 2.4 review and
  manages PS-CAPTURE-MEDIA-001 planning.
- **Claude Code / Fable:** self-managed implementation writer for assigned
  front-end packages, including a protected owner surface when explicitly
  assigned. Claude Co-Work management does not grant Claude Code ownership of a
  manager or writer branch.
- Each writer owns implementation, complete-diff review, correction, tests,
  evidence, PR readiness, and, after Pete/designated-manager acceptance, Azure
  release/closeout. Every report states `Pass`, `Conditional`, or `Fail`.
- One manager per package and one writer per branch remain mandatory. Parallel
  managers may coordinate separate packages but may not overlap shared-file
  reservations. A branch/SHA handoff is required when
  a different writer continues; it is not required merely because the same
  self-managed writer reached self-review or PR readiness.

## Verified released foundation

Before this visual-integrity governance package, Azure `main` was
`5488819ad13d3f411319d7e184fde3779d62b8d2` after PR 70 and pipeline 97.
Always fetch for the actual current tip.

The visual-integrity governance package then squash-merged through Azure PR 71
at `28ec01097677219bbe466ff2c731707d0e4a2b89`; pipeline 99
(`20260719.7`) passed Build and Deploy. This released Bible v2.4, the Owner
Visual Integrity Standard, and this handoff without changing website behavior.

The later Story-composition direction adopts Bible v2.5 and Roadmap v2.4. The
next manager must treat the current baseline pointers as controlling and fetch
`origin` for the exact release evidence.

That direction squash-merged through Azure PR 73 at
`aaee6e563a94e19d1786ded3f636d8376e20d500`; pipeline 102
(`20260719.10`) passed Build and Deploy. Production behavior remained
unchanged, including the canonical My Story redirect and the protected Capture
sign-in boundary.

- Public résumé refinement: PR 62 / pipeline 83.
- Capture lifecycle: PR 63 / pipeline 85.
- Canonical Moment: PR 66 / pipeline 91.
- Private placement reference foundation: PR 68 / pipeline 93.
- Placement governance closeout: PR 69 / pipeline 95.
- Voice activation package: PR 70 / pipeline 97.
- Visual-integrity governance and manager handoff: PR 71 / pipeline 99.
- Member-directed Story composition authority: PR 73 / pipeline 102.
- Private Voice Capture implementation: PR 75 at
  `eede8565d703a466bd788962d494e8b385b53409` / pipeline 105.
- Self-managed delivery lanes and Claude Voice correction allocation: PR 76 at
  `fe03d49ca57bde2c4d0bfc4c66726c132da81ebf` / pipeline 107.
- Protected Voice visual parity: accepted Claude tip
  `e32b31d7c351ac2f8601a4467bcd1c9450f52c3b`, Azure PR 80, merge
  `864a79d1bc1fc61e62f2d2a544dd54a01ebdcb82`, pipeline 113
  (`20260719.21`) Build and Deploy passed.
- Voice governance closeout: Azure PR 81, merge
  `5cc5b69346ee354bcc36248f7ee5724ce13c9d08`, pipeline 115
  (`20260719.23`) Build and Deploy passed; public, Interview, Voice walkthrough,
  and protected Capture auth-boundary checks passed.
- Production checks after PR 70: `/`, `/petec/resume`, and
  `/interview-studio` returned 200; `/app/capture` redirected a signed-out
  visitor to sign-in.

Reusable and not to be rebuilt: real identity and two-owner isolation, Owner
Settings, private text Capture lifecycle, canonical Moment confirmation,
private exact-version Placement reference foundation, refined public résumé,
public browser-local Interview Studio, and Deep Navy Gold foundations.

## Completed lane - PS-VOICE-001

### Honest current state

Voice is implemented, deployed, visually accepted, and closed. Production
private Blob/RBAC, managed-identity Speech, SQL migration/verification, Azure
PR 75, pipeline 105, and Pete's signed-in functional validation remain the
backend evidence. Claude Code completed the protected visual correction,
self-certified `Pass`, and relinquished exact tip
`e32b31d7c351ac2f8601a4467bcd1c9450f52c3b`. Pete and ChatGPT Work accepted the
real responsive implementation at V3. Azure PR 80 released it at
`864a79d1bc1fc61e62f2d2a544dd54a01ebdcb82`; pipeline 113 passed Build and
Deploy.

Live verification returned 200 for `/` and the Voice walkthrough, the expected
signed-out 302 from `/app/capture` to sign-in, and the accepted Voice CSS/JS
signatures from production. The available verification browser had no signed-in
member session, so no new post-deploy authenticated screenshot or repeated real
Speech transaction is claimed. The accepted implementation evidence remains the
visual proof; pipeline and live asset/auth checks are the V4 release proof.

Preserve `C:\Users\peter\Documents\portfolio-voice-001` and
`C:\Users\peter\Documents\portfolio-voice-visual-parity`; do not switch, clean,
edit, stash, or reuse them. They are historical references, not active lanes.

### Required product outcome

The first slice is short private voice recording (3 minutes / 20 MB, `en-US`),
private original audio in Azure Blob Storage, Azure Speech transcription through
managed identity, editable transcript review, and explicit **Save private
Capture** into the existing lifecycle. Text remains available. No Moment,
Placement, Journal, résumé, Studio, share, audience, or publication is created
automatically.

### Closed visual contract

The released UI satisfies `OWNER_VISUAL_INTEGRITY_STANDARD.md`:

- the homepage Voice walkthrough is the minimum visual/interaction authority;
- the real protected UI must be recognizably the same or better;
- Speak and Type are both first-class opening choices;
- switching paths must not silently destroy member work;
- microphone, waveform/timer, stop, playback/retry, editable transcript,
  privacy, explicit save, failures, desktop/mobile/keyboard/zoom evidence, and
  owner/manager visual acceptance are mandatory.

The approved future Community, Connections, selected-audience, My Story, Slate
Board, résumé, attachment, AI-draft, and publication affordances appear only as
polished, disabled `Coming later` scaffolding. **Save private Capture** remains
the only live completion action. Later activation requires separate backend,
authorization, product, visual, and release packages.

## Active lane 1 - PS-INTERVIEW-PUBLIC-GATE-001

### Product decision already approved

Keep the current interactive, unauthenticated `/interview-studio` under Approach
A. Preserve written answers, real coaching requests, Interview AI, comparison,
browser-local history, and local camera rehearsal. Keep the route light-first
Deep Navy Gold. Pete is a clearly labeled public demo profile, not signed-in
identity. Current mode names are Interview Me, Interview AI, and Video Practice.
The current written-practice flow remains primary.

### Design state and selected direction

The exact owner authority is
`C:\Users\peter\iCloudDrive\Documents\Career\Website\Changes\Interview Studio\ChatGPT Image Jul 19, 2026, 12_09_58 PM (5).png`.
Image 5 Concept A, **Editorial Studio Ledger**, controls default/light. Image 5
Concept C, **Cinematic Studio**, controls optional dark. Image 1A and Image 2A
are not co-authorities. Light and dark are two themes of the same public route,
semantic DOM, functionality, state machine, truth, and accessibility behavior;
dark is not a separate or authenticated product. File
`09_DUAL_THEME_VISUAL_AUTHORITY_AND_CLAUDE_BRIEF.md` is the definitive Claude
design/feasibility package. It is not yet implementation authority. Known
corrections remain:

- use one dominant opening CTA;
- keep **Interview Me** as the mode name; "written practice" may describe it;
- show Continue local draft only when a real browser draft exists;
- split video permission, recording, and playback/delete into truthful states;
- map Improve Answer to the existing public coaching behavior and do not invent
  a save or account capability.

### Required next design gate

The assigned Codex manager-review session must receive and evaluate Gate 2.4:
the complete nine current-public screens in both controlling themes (18 primary
exports),
editable responsive source, mobile portrait/landscape, 200% reflow, keyboard
focus, reduced motion, long content, failure and media-denied states, component
inventory, theme persistence/no-state-loss, truth/accessibility review, and
implementation mapping. It should
also review the relationship to the separate homepage Interview Studio
walkthrough. The current walkthrough is an accepted, live, illustrative
pre-convergence release. It must not replace or visually control the real
public Studio, and final 5A/5C homepage parity remains a later separate
closeout.

The Codex session creates a clean review branch, records the package matrix,
truth/accessibility review, implementation mapping, and `Pass`, `Conditional`,
or `Fail` result, then pushes and gives Claude Co-Work the exact branch/SHA.
It does not edit product implementation files.

Then:

1. Claude Co-Work receives and confirms the durable Codex review as designated
   package manager.
2. Claude Code/Fable performs feasibility review only.
3. Pete and the designated manager approve the final visual baseline.
4. Only then may Claude receive real Studio implementation authorization on a
   fresh branch. Claude records the implementation architecture first, then
   self-manages implementation, tests, evidence, and `Pass` review.
5. Pete and the manager accept the real implementation and visuals; Azure PR,
   pipeline, and live verification close the real Studio release.
6. Only after that live verification may Claude start a fresh downstream branch
   and converge the already-live illustrative walkthrough on the exact released
   5A/5C Studio. The updated projection receives separate acceptance, Azure
   release, and live homepage verification.

Pete accepted the fixed illustrative homepage walkthrough for its current
purpose. Claude's exact source tip
`90d035a25344c850e6ed732c1efb6e4d0a240787` on
`work/2026-07-19-home-interview-demo-001` squash-merged through Azure PR 86 at
`a98cced519a1f853ad9f4462fd438efa67d6f260`. Automatic pipeline 122
(`20260719.30`) passed Build and Deploy for that exact merge. Automatic
pipeline 123 (`20260719.31`) then passed for descendant main
`6cb49f135cc3a2749dd4539f8261d176b43dad9a`, with no changes in demo-owned
paths. Manual pipeline 124 (`20260719.32`) also passed for that same SHA and
was redundant evidence, not a CI-trigger failure.

The live homepage, versioned demo CSS, and versioned demo JavaScript return 200.
The four fixed stages, explicit fictional/no-input/no-AI/no-storage truth, final
real-Studio link, desktop modal, and 390px reflow passed manager review. This
closes the current demonstration only. Its paper-light dark modal and
Voice-default copy remain known downstream 5A/5C convergence work. Preserve the
historical worktree; do not delete or reuse it during the active Studio gate.
File
`10_REAL_STUDIO_AND_HOMEPAGE_DEMO_CONVERGENCE.md` contains the definitive
real-Studio and demo instructions.

That sequencing record is authoritative on `origin/main`: implementation tip
`9ea02196f6410fbbe40aa60355f6013815a7e625`, Azure PR 83, squash merge
`cee015f6291fe5460a6a5d5795c445bb6b25c6f9`, and pipeline 117
(`20260719.25`) with Build and Deploy passed. Live `/`,
`/interview-studio`, and `/interview-studio/history` returned 200; protected
`/app/capture` kept its signed-out redirect. This was a governance-only release
and is not evidence that the new Studio or the later 5A/5C-converged homepage
projection is implemented. The separate PR 86 release is evidence only for the
current pre-convergence illustration.

Do not authorize Claude implementation from the three-direction art package
alone.

## Active lane 2 - PS-CAPTURE-MEDIA-001

Claude Co-Work is the designated manager for Capture Media planning. No remote
Capture Media implementation branch was visible when this package was
activated. Treat any unpushed session work as non-authoritative until it is on a
clean Azure task branch with an exact full SHA.

The manager must inventory the released private Voice/Blob/Speech foundation,
keep Voice separate, and define photo, video, and document source slices through
the shared owner, provenance, review, lifecycle, export/delete, accessibility,
failure, infrastructure, test, rollout, and rollback contracts. It then selects
one first vertical slice and assigns one implementation writer/branch. Planning
does not mean implemented, deployed, or live.

## Planned package - PS-PROJECTS-001

Projects are planned under Roadmap Phase 10 and are not an active writer lane.
The future product begins as a private-first Project Workspace that connects
exact governed records and relationships without copying canonical facts. Any
purpose- and audience-specific Project Projection is a separate later object
with explicit draft, preview, publication, revocation, and correction behavior.

The first entry gate is defined in
`docs/initiatives/PS-PROJECTS-001/README.md`: validate Project versus Work versus
Slate Board boundaries, select one production-intent private-workspace visual
authority, baseline the aggregate/authorization/exact-version architecture,
and assign one manager and writer on a fresh branch. Do not revive the retired
Pete-only Projects page, treat Board notes as canonical Projects, build a task
manager, or interrupt Interview Studio and Capture Media.

## Planned package - PS-ASK-PETE-AI-001

Ask Pete AI is planned under Roadmap Phase 11 and is not an active writer lane.
The current production assistant remains public, typed, and grounded only in
approved public profile knowledge. The future product discussion must explore
Type, Speak, PDF/DOCX/TXT, and screenshot/OCR inputs while defining an explicit
public Ask Pete AI versus private owner-analysis boundary.

The first gate is the owner discussion in
`docs/initiatives/PS-ASK-PETE-AI-001/01_DISCOVERY_AGENDA.md`. Do not assign an
implementation writer until the role, primary scenario, inputs/outputs,
complete visual authority, privacy/lifecycle, architecture, AI-safety,
evaluation, homepage impact, and release gates are approved. This package must
not interrupt the active Interview or Capture Media lanes.

## Owner-wide visual decision

The current Bible is v2.6 and the
`OWNER_VISUAL_INTEGRITY_STANDARD.md` is part of mandatory startup. Selected
demonstrations are visual promises: the real experience must match or exceed
them. Visual polish is a release gate across all user-facing PeerSlate work,
alongside function, privacy, security, accessibility, tests, and deployment.
The current homepage overall is not the target; a broader homepage redesign is
still future work.

Every logged-out homepage section is also a governed product projection. When
the real product changes materially in function, hierarchy, theme, truth, or
visual finish, the affected homepage section must be updated in the same wave
or through an exact downstream parity package. The real product is upstream
authority. The manager may let it release first when sequencing requires that,
but must keep homepage parity open until the visitor-facing section is current,
showcase-quality, separately accepted, released, and verified. Voice and
Interview Studio are current examples; the rule applies to every homepage
product section.

## Owner Story composition decision

The future authenticated My Story editor is member-directed. Members shall be
able to move and resize supported notes, text, pictures, and media; control
overlap/layering; undo and restore; preview desktop/tablet/mobile and exact
audiences; save a private layout draft; and publish separately. Dragging requires
keyboard and structured-editor equivalents. AI may propose a layout but may not
silently apply, save, overwrite, or publish it.

Pete's concrete acceptance case is the current **I went back at 36** card: he
must be able to make it smaller or move it so the sailboat in the Maui image
remains visible. `PS-STORY-COMPOSER-001` is planned future work, not active, and
does not interrupt Voice or Interview.

## Roadmap looking forward

Near-term sequencing is:

1. finish Interview Gate 2.4, feasibility review, owner approval, and then the
   bounded public Studio implementation;
2. after the real Studio is accepted and live, open the separate downstream
   branch that converges the existing live homepage walkthrough on that exact
   release;
3. choose the next backend consumer or owner-shell slice without automatically
   starting Journal;
4. build the real owner Home/viewer modes and authenticated Studio only through
   separately approved identity, persistence, authorization, and lifecycle
   packages;
5. conduct the broader public/homepage visual convergence after its entry gate;
6. hold PS-PROJECTS-001 until its boundary validation, private-workspace visual
   authority, joint architecture baseline, and explicit activation gate pass;
7. hold PS-ASK-PETE-AI-001 Phase A discovery when Pete is ready; do not start
   implementation before the multimodal, public/private, visual, architecture,
   safety, and homepage-parity gates pass;
8. schedule PS-STORY-COMPOSER-001 only after its full authenticated projection,
   layout persistence, accessible interaction, and publication design gate;
9. run a two-member founding alpha with Pete and Danielle, then structured
   feedback, fixes, a small invited cohort, and measured rollout.

Journal UI remains on hold. Do not duplicate Capture or Moment text, create a
second résumé dataset, imply account-backed public Studio history, or treat a
backend reference as a visible member feature.

## First actions for the next manager session

1. Fetch `origin` and verify the exact current `main`, current Bible pointer,
   pipeline, and production routes.
2. Confirm the self-managed delivery workflow is merged and green.
3. Inspect all worktrees without changing them; confirm each active branch has
   one writer and non-overlapping files.
4. Treat Voice as released and closed; preserve its worktrees and require a new
   package for any future refinement.
5. Receive the Codex Interview Gate 2.4 review branch/SHA/report in Claude
   Co-Work, confirm it, then send the accepted package to Claude Code/Fable for
   feasibility review.
6. Obtain Pete/designated-manager visual approval before Interview code.
7. Claude Co-Work completes Capture Media manager planning before assigning an
   implementation writer.
8. Apply the homepage-impact and parity check to every user-facing package;
   keep exact downstream parity packages visible until their homepage sections
   are accepted and live.
9. Keep Interview, Capture Media, planned Projects and Ask Pete AI, and homepage parity
   status and next gates current in
   the repository after each material handoff or release.

## Paste-ready kickoff for a designated manager session

> You are the designated PeerSlate package manager. Open and follow
> `START_HERE.md`, then read
> `docs/governance/MANAGER_SESSION_HANDOFF.md` and every authority file it names.
> Fetch authoritative Azure `origin/main` and inspect all worktrees before any
> write. Apply the self-managed lane model: each assigned writer implements,
> reviews its complete diff, corrects issues, runs tests/evidence, prepares the
> PR, and returns `Pass`, `Conditional`, or `Fail`; after focused Pete/manager
> acceptance the same writer completes Azure release/closeout. Preserve the
> completed PS-VOICE-001 worktrees; Voice is released and any later change
> requires a new package. Preserve its accepted Speak/Type, privacy, lifecycle,
> accessibility, and walkthrough-parity contracts.
> Continue Interview only at Gate 2.4 design review. Image 5 Concept A controls
> default/light and Concept C controls optional dark for the same public Studio.
> Require file `09`'s complete dual-theme package, feasibility, and approvals.
> Maintain honest implementation, demonstration, deployment, and
> live-production boundaries. For every user-facing package, identify any
> homepage product projection and require the same-wave update or exact
> downstream parity package defined by the Owner Visual Integrity Standard.
> Keep `PS-PROJECTS-001` planned until its boundary, visual, architecture, and
> owner-route entry gates pass; it is a private-first connected Project system,
> not the retired public fixture or a task-management suite.
> Keep `PS-ASK-PETE-AI-001` planned until Pete completes the product discussion;
> Ask Pete AI is the correct name, not PAI.

## Paste-ready kickoff for the new Codex Interview Gate 2.4 session

> Open authoritative Azure `origin/main` and follow `START_HERE.md`. You are the
> bounded manager-review session for `PS-INTERVIEW-PUBLIC-GATE-001` Gate 2.4,
> not the implementation writer. Create a clean
> `work/YYYY-MM-DD-interview-gate-24-review` branch. Review the attached complete
> Image 5 Concept A light / Concept C dark package against files `01` through
> `07` and `09_DUAL_THEME_VISUAL_AUTHORITY_AND_CLAUDE_BRIEF.md`: nine
> full-screen states in both themes (18 primary exports), responsive source,
> mobile portrait/landscape, focus, 200% reflow, reduced motion, long content,
> failure/media-denied states, truth/accessibility, component inventory, shared
> DOM/state architecture, theme persistence/no-state-loss,
> homepage walkthrough separation, and implementation mapping. Do not edit
> Interview product code. Return `Pass`, `Conditional`, or `Fail`, commit/push
> the durable review, and give Claude Co-Work the exact branch/full SHA and
> report for manager confirmation and Claude Code feasibility review.

## Paste-ready kickoff for Claude Co-Work

> Open the authoritative Azure repository and follow `START_HERE.md`. You are a
> package-designated PeerSlate session manager with the same governed manager
> authority as ChatGPT Work/Codex. Read `MANAGER_SESSION_HANDOFF.md`, current
> authority/state/initiatives, and every assigned package. Receive writer or
> manager-review branches read-only by exact full SHA; rely on coherent
> self-certification while escalating conflicts; keep implementation,
> demonstration, deployment, and live status separate; and close accepted work
> through Azure evidence. You currently receive the Codex Interview Gate 2.4
> review and manage `PS-CAPTURE-MEDIA-001` planning. Do not take over Claude Code
> implementation branches without explicit writer relinquishment. Capture Media
> planning must define bounded photo/video/document slices and assign a separate
> writer before any implementation claim.
