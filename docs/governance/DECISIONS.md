# PeerSlate Manager Decision Log

This is an append-only operational decision record. The current Bible and Roadmap remain the product authority.

## 2026-07-18 — Adopt Bible and Roadmap v2.3

- Bible v2.3 and Roadmap v2.3 are the current product and sequencing authority.
- Older v1.1-v1.4 and Iris/Direction C material remains history or non-conflicting supporting detail.
- Deep Navy Gold is the approved shared theme.

## 2026-07-18 — Assign ChatGPT Work as PeerSlate manager

- Owner decision: ChatGPT Work coordinates the program.
- Manager responsibilities: authority records, package definitions, lane sequencing, file-boundary review, completion-report review, merge readiness, and release verification.
- ChatGPT Codex is the backend convergence writer. Claude Code is the public front-end writer.
- The manager does not absorb product implementation unless the owner explicitly reassigns a package.

## 2026-07-18 — Start Capture and résumé as the first parallel wave

- PS-CAPTURE-002 and PS-RESUME-PUBLIC-REFINE-001 may run in parallel after PS-BASELINE-001 merges.
- They must start from the same then-current `origin/main`, use separate branches, and not share writable files.
- Interview Studio work is not bundled with the résumé. It waits for PS-INTERVIEW-PUBLIC-GATE-001.

## 2026-07-18 — Bound the Capture lifecycle package

- The original text in `dbo.captures` remains the preserved source input. Corrections create owner-scoped revisions rather than overwriting the original.
- Archive is reversible through restore. Delete is explicit and irreversible for source text and its revisions; only a body-free audit tombstone may remain.
- Export is a versioned, owner-scoped per-capture JSON contract in this package. Account-wide portability/deletion remains a later data-rights package.
- Minimal controls inside the protected Capture page belong to the backend package. Public templates, global theme/navigation, authentication architecture, Journal UI, Moment, and placement are excluded.

## 2026-07-18 — Close the first parallel wave

- PS-RESUME-PUBLIC-REFINE-001 was manager-reviewed, squash-merged through Azure PR 62, deployed by successful pipeline 83, and verified at `/petec/resume`.
- PS-CAPTURE-002 passed responsive mobile proof, isolated SQL apply/verify/rollback/reapply, production forward migration/verification, manager review, Azure PR 63, successful pipeline 85, and protected production-route checks.
- The résumé and Capture task branches are released. Their local worktrees may remain only as preservation references until deliberate cleanup; they are not active writing lanes.

## 2026-07-18 — Start the second parallel wave

- Claude Code owns PS-INTERVIEW-PUBLIC-GATE-001. `/interview-studio` remains a public demonstration; `/interview-studio/history` is browser-local demonstration state. `/app/interview-studio` is the reserved future authenticated owner route and must not be simulated by the public package.
- ChatGPT Codex owns PS-MOMENT-001. The required boundary is one pinned Capture source version → editable private proposal → explicit member confirmation → source-linked canonical Moment.
- A Capture correction never silently rewrites a Moment. Moment confirmation never publishes or places content. PS-PLACEMENT-001 remains the next backend gate.
- The two packages use separate branches and file reservations and may proceed in parallel after this manager setup is on current `origin/main` with a green pipeline.
- Voice and other media intake remain later packages; the next backend work proves the review/canonicalization boundary using the shipped text source first.

## 2026-07-18 — Close PS-MOMENT-001 and activate reference-only Placement

- PS-MOMENT-001 passed corrected manager review, isolated SQL concurrency/rollback proof, production migration verification, Azure PR 66, pipeline 91 Build and Deploy, and protected production-route checks.
- The confirmed Moment boundary is now reusable. A confirmed Moment remains private and does not itself publish, share, place, alter a résumé, or create Journal content.
- PS-PLACEMENT-001 is the next Codex backend package. One explicit owner action may create a private reference from the exact confirmed Moment version to an existing owner-owned private/unpublished Slate destination.
- The placement record stores keys, ownership, lifecycle, actor, and timestamps only. It must not copy Capture text, Moment narrative, destination content, or a purpose-specific presentation snapshot.
- Creating or removing a placement must not create or edit the destination, change visibility/audience/publication, create an access grant, or update Story, Work, Project, résumé, Studio, Journal, Feed, or public pages.
- Downstream consumption and purpose-specific wording remain separate later packages. Journal remains on hold.

## 2026-07-18 - Select private Voice Capture as the next backend package

- Owner decision: start Voice Capture before owner Home/viewer-mode work.
- PS-VOICE-001 is one complete private path: short recording, private original audio, server-side transcription, member correction/review, and explicit save into the existing Capture lifecycle.
- The original audio is retained privately with the Capture as source evidence and removed through an explicit, retryable deletion workflow. The first slice is `en-US`, 3 minutes, and 20 MB.
- App Service uses managed identity for private Blob Storage and Azure Speech. No storage/Speech key, public container, public Blob URL, reusable SAS URL, or private payload in logs/audit metadata is allowed.
- Voice confirmation creates one private `capture_type = voice` record only. It never automatically creates or changes a Moment, Placement, Journal entry, resume, Interview Studio record, audience, share, or publication.
- Text Capture remains available whenever microphone access, browser support, upload, storage, or transcription fails.
- ChatGPT Codex implements and proves PS-VOICE-001 without touching production. ChatGPT Work retains production infrastructure, migration, PR, deployment, and live-verification authority.

## 2026-07-18 - Make visual integrity and demonstration parity constitutional

- Adopt Bible v2.4 as the current Bible, superseding v2.3 while retaining
  Roadmap v2.3 and Sync Standard v1.1.
- Owner decision: PeerSlate must be gorgeous, professional, and polished across
  every user-facing experience. Functional correctness alone is not completion.
- An owner-approved production-intent demonstration, walkthrough, mockup, or
  storyboard is a binding visual minimum. The real product must be recognizably
  the same interaction model and match or exceed its composition, hierarchy,
  clarity, and finish.
- Demonstrations must honestly label illustrative versus live behavior, storage,
  transmission, identity, privacy, and future capability. That honesty does not
  permit a later visual downgrade.
- Material user-facing work requires named comparison evidence and Pete plus
  ChatGPT Work visual acceptance before merge unless Pete explicitly delegates
  the gate.
- The homepage Voice walkthrough is the minimum visual authority for the real
  protected Voice Capture experience. Speak and Type are first-class opening
  paths. The real flow still ends at review and explicit private Capture save.
- Direction A, Editorial Studio Ledger, is selected for the current public
  Interview Studio design lane. It is not implementation-ready until Gate 2.4's
  complete nine-screen responsive source, truth/accessibility review, Claude/
  Fable feasibility review, and owner/manager acceptance pass.
- Pete authorized a separate future homepage Interview Studio walkthrough. It
  does not replace the real interactive public Studio and requires its own
  package/branch after the design is frozen.
- The current homepage overall is not the approved final quality baseline. A
  broader homepage/public convergence remains a later gated initiative.

## 2026-07-18 - Make My Story composition member-directed

- Adopt Bible v2.5 and Roadmap v2.4, superseding Bible v2.4 and Roadmap v2.3.
- The future authenticated Story Composer shall let members move and resize
  supported notes, text, pictures, and media and control overlap/layering.
- Dragging shall have keyboard and structured-editor equivalents. Spatial
  presentation shall preserve semantic reading order, responsive flow, touch,
  200-percent zoom, reduced motion, and failure recovery.
- Layout metadata is owner-scoped, versioned projection data stored separately
  from canonical Story content. Saving a layout draft and publishing a Story are
  separate explicit actions with exact audience preview.
- AI may propose a layout but may not silently apply, overwrite, save, or publish
  it. The member remains the authority over composition and audience.
- Pete's first acceptance example is the **I went back at 36** card on the Maui
  image: he must be able to shrink or move it so the sailboat remains visible.
  The example is validation evidence, not Pete-specific reusable logic.
- Reserve `PS-STORY-COMPOSER-001` as planned future work. This decision does not
  change the current public Story or interrupt active Voice and Interview work.

## 2026-07-19 - Adopt self-managed delivery lanes

- Owner decision: Codex and Claude self-manage their assigned branches through
  implementation, complete-diff review, correction, tests, evidence, PR
  readiness, and post-acceptance Azure release/closeout.
- ChatGPT Work remains the task manager, shared-authority and file-boundary
  coordinator, visual authority, exception escalation point, and final
  product-acceptance room. It does not routinely repeat a coherent writer
  self-audit.
- Every writer returns a `Pass`, `Conditional`, or `Fail` self-certification
  with exact branch/SHA, tests, screenshots, parity/deviation evidence,
  conflicts, limitations, pipeline, and production proof as applicable.
- Pete and ChatGPT Work still accept material user-facing work. That focused
  acceptance may rely on the self-certified report and real-product review.
- A branch still has one writer; Azure PR/squash/pipeline rules, server-enforced
  trust boundaries, credential restrictions, and honest implementation versus
  deployment versus live status remain unchanged.
- Package-local architecture and completion records travel with the branch.
  Shared current-state records change only under explicit reservation. The
  Bible changes only for constitutional product direction, not routine release
  tracking.

## 2026-07-19 - Reopen Voice visual acceptance and preserve future scaffolding

- Pete verified that the deployed signed-in Voice workflow functions, then
  withdrew visual acceptance because the protected desktop and mobile
  experience does not match the approved homepage/feed walkthrough.
- Claude Code owns the self-managed frontend correction on a fresh branch from
  current `origin/main`; the original Codex Voice worktree remains preserved.
- Community, Connections, selected audiences, My Story, Slate Board, résumé,
  photo/video/document, AI-assisted draft, and publication may be represented
  now as polished, clearly disabled `Coming later` scaffolding.
- The scaffolding is not authorization or simulated completion. **Save private
  Capture** remains the only live completion action until separately approved
  backend and destination packages activate later capabilities.

## 2026-07-19 - Make the session-manager role portable and activate Capture Media planning

- Owner decision: a ChatGPT Work/Codex manager session or Claude Co-Work may
  perform the same package-management role when named by the active initiative.
- Each package has exactly one designated session manager at a time. Different
  managers may coordinate non-overlapping packages, but shared-governance-file
  reservations and writer branches may not overlap.
- Claude Co-Work management is distinct from Claude Code implementation. A
  manager reviews a writer branch read-only unless exact branch/SHA ownership is
  explicitly transferred.
- A Codex manager session may review the complete Interview Studio Gate 2.4
  design package and return its branch/SHA/report to Claude Co-Work. Claude Code
  implementation remains blocked until feasibility and Pete/designated-manager
  visual approval pass.
- Claude Co-Work is designated manager for PS-CAPTURE-MEDIA-001 planning. This
  activates requirements, architecture, decomposition, and writer allocation;
  it does not claim that photo, video, or document Capture is implemented,
  deployed, or live.

## 2026-07-19 - Accept and release Voice visual parity

- Pete and ChatGPT Work accepted PS-VOICE-VISUAL-PARITY-001 as **Pass** at the
  relinquished Claude Code tip
  `e32b31d7c351ac2f8601a4467bcd1c9450f52c3b` after the manager correction pass.
- Azure PR 80 squash-merged the accepted manager closeout as
  `864a79d1bc1fc61e62f2d2a544dd54a01ebdcb82`; pipeline 113
  (`20260719.21`) passed Build and Deploy for that exact merge.
- Live verification proved the public routes, deployed Voice CSS/JavaScript
  signatures, and the protected `/app/capture` sign-in boundary. The available
  production browser was signed out, so this closeout does not claim a new
  authenticated production screenshot or repeat the already completed real
  Azure Speech transaction.
- PS-VOICE-001 and its visual-parity correction are complete, accepted,
  deployed, live, and closed. The released privacy, lifecycle, Speak/Type,
  accessibility, and visual contracts remain binding.
- Disabled future-destination scaffolding remains non-functional. Activating
  Community, Connections, Story, Slate Board, resume, media attachment, AI-post,
  sharing, or publication behavior requires a separately authorized package,
  branch, evidence set, visual acceptance, and Azure closeout.

## 2026-07-19 - Select 5A light and 5C dark for the current public Interview Studio

- Owner decision: the exact source image
  `C:\Users\peter\iCloudDrive\Documents\Career\Website\Changes\Interview Studio\ChatGPT Image Jul 19, 2026, 12_09_58 PM (5).png`
  controls the current public Studio visual system. Concept A, Editorial Studio
  Ledger, controls default/light; Concept C, Cinematic Studio, controls optional
  dark. Image 1A and Image 2A are not co-authorities.
- Light and dark are themes of the same `/interview-studio`, with one semantic
  DOM, information architecture, action set, state machine, truth boundary,
  responsive behavior, and accessibility model. Dark is not a second product,
  authenticated route, private workspace, or expanded feature set.
- The current written-practice flow remains primary. Changing theme must not
  reset drafts, goals, answers, selected modes, browser-local history, media
  state, focus, dialogs, or scroll position.
- The full nine-screen current-public package must cover both themes and all
  responsive, focus, reflow, reduced-motion, long-content, unavailable, error,
  retry, and recovery states. Mobile reflows and scrolls; it does not shrink the
  desktop composition or hide essential truth.
- This decision supersedes the earlier assumption that Concept C could only be
  banked for a future authenticated Studio. It does not authorize product code.
  Claude/Fable feasibility plus Pete and designated-manager visual approval
  must pass before a fresh implementation branch may start.

## 2026-07-19 - Make the homepage Interview walkthrough a downstream projection

- Owner decision: finish and approve the real 5A-light/5C-dark Studio first;
  then architecture, implement, accept, release, and verify that real Studio;
  only then converge the separate homepage walkthrough on the exact released
  product.
- The real `/interview-studio` is the upstream visual and product authority.
  The homepage walkthrough is a short static projection, not a co-authority or
  substitute for the product.
- The observed clean pushed demo branch
  `work/2026-07-19-home-interview-demo-001` at
  `358e7eea304a2b4d4008031ea8f51c523380ee4f` is a parked interaction
  prototype. Preserve its modal, responsive/accessibility, no-JavaScript, and
  no-side-effect shell. Do not merge or deploy its stale paper-light dark
  treatment or Voice-first product framing.
- The converged demo must map each fixed step to an exact released real-Studio
  state, express 5A in light and 5C in dark, keep written Interview Me primary,
  and remain static with no network, storage, microphone, camera, or real
  coaching behavior.
- Real Studio implementation and demo implementation require separate exact
  branch/SHA, Pete/manager visual acceptance, Azure PR, squash-merge SHA,
  pipeline, and live verification evidence.

## 2026-07-19 - Accept the current homepage Interview walkthrough as a live pre-convergence illustration

- Pete accepted the fixed four-state homepage Interview walkthrough for its
  current illustrative purpose. Claude's exact source tip
  `90d035a25344c850e6ed732c1efb6e4d0a240787` released through Azure PR 86,
  squash merge `a98cced519a1f853ad9f4462fd438efa67d6f260`, and automatic pipeline
  122 (`20260719.30`). Live desktop and 390px manager review passed the poster,
  modal, four deterministic states, explicit truth labels, and final real-Studio
  link.
- This is an explicit owner-approved interim release of the demonstration. It
  does not reverse the real-Studio-first authority decision, make the current
  walkthrough a co-authority, approve the real 5A/5C Studio implementation, or
  close homepage projection parity.
- The current Voice-default framing and paper-light dark modal are accepted only
  as known pre-convergence limitations. After the exact 5A-light/5C-dark real
  Studio is accepted, released, and verified live, a fresh downstream branch
  must map and release the updated homepage projection.
- Automatic pipelines 122 and 123 both fired successfully. Manual pipeline 124
  was an additional successful deployment of descendant main and is not
  evidence that the Azure CI trigger is disabled.

## 2026-07-19 - Register Ask Pete AI for multimodal product discovery

- Owner clarification: the product name is **Ask Pete AI**, not "PAI."
- The current public typed Ask Pete AI remains real and unchanged. It is not
  evidence that private owner retrieval, voice, attachments, OCR, or job-
  posting analysis already exists.
- Reserve `PS-ASK-PETE-AI-001` as planned Roadmap Phase 11 work. The package
  begins with an owner discussion to define the role, public/private modes,
  first scenario, inputs, outputs, exclusions, success measures, and product
  name relationships before design or implementation.
- The discovery must explore Type, Speak, PDF/DOCX/TXT documents, and one or
  more PNG/JPEG screenshots such as job postings. Extracted/OCR text and source
  spans require member review before consequential analysis.
- The future product stays private-first, source-grounded, correctable, and
  deletable. It is not a job board, job feed, fit oracle, automatic application
  tool, public index, or unreviewed editor of canonical Slate records.
- No discovery manager, implementation writer, product branch, migration,
  dependency, design authority, start date, or implementation authorization is
  assigned by this docket decision.

## 2026-07-19 - Require cross-product homepage projection parity

- Owner decision: every logged-out homepage section that presents or links a
  PeerSlate product must be individually showcase-quality - in Pete's words,
  "staggeringly beautiful" - and must remain truthful and current with the real
  product.
- The accepted and live real product is upstream authority. A homepage section
  is a distilled public projection, not a parallel design or product authority.
- Every material product or visual change requires a homepage-impact
  assessment. When a related homepage section exists, update it in the same
  release wave when safe or activate an exact downstream parity package after
  the real product releases. Do not report homepage parity closed while the
  public projection remains stale.
- Parity covers function, capability truth, product names, hierarchy, dominant
  action, themes, recognizable visual language, responsive/accessibility
  behavior, canonical links, and professional finish. It does not require a
  literal copy of the application screen.
- Voice Capture and Interview Studio are the current named examples. The rule
  applies equally to Ask Pete AI, Living Resume, My Story, Slate Board, and
  every other present or future product section on `/`.
- Each affected real-product package and homepage package requires its own
  desktop/mobile comparison, truth review, Pete/designated-manager acceptance,
  Azure release, and live verification evidence.

## 2026-07-19 - Establish Projects as planned Phase 10 product architecture

- Owner direction: Projects are a natural later PeerSlate expansion and should
  be defined now as a real connected product system, without interrupting the
  early release sequence or prematurely implementing it.
- Adopt Bible v2.6 and Roadmap v2.5. Preserve the production, visual-integrity,
  member-directed Story, delivery, and active-lane baseline while adding the
  Projects covenant and `PS-PROJECTS-001` Phase 10 allocation.
- A Project is a private-first member-owned container for a meaningful endeavor.
  It connects exact approved canonical records and relationships without
  copying authoritative Moment, source, role, outcome, Story, resume, or
  publication content.
- The authenticated Project Workspace and any purpose- and audience-specific
  Project Projection are separate lifecycle and publication objects. Editing or
  completing a Project never publishes it.
- Work remains the broader roles-and-contributions domain. Slate Board Project
  notes are planning objects, not canonical Projects. The retired Pete-only
  Project fixture and its redirects are historical behavior, not the future
  product system of record.
- AI may propose structure, relationships, questions, reflection, milestones,
  or wording. Deterministic software and explicit member actions control
  Project creation, lifecycle, relationships, audience, sharing, publication,
  archive, deletion, and collaboration.
- PeerSlate Projects are not a Jira/Trello-style task manager, timesheet,
  procurement tool, issue tracker, or enterprise delivery suite.
- Reserve `PS-PROJECTS-001` as planned, not active. Its first later slice is the
  owner-only Project foundation and Ledger using exact-version Moment Placement;
  public projections, collaboration, task management, homepage work, and route
  revival remain outside that slice and require later gates.

## 2026-07-20 - Restart Journal as the memory profile and reconnect Member Intelligence and Activation

- Peter explicitly lifted the Journal hold after supplying Foundation Edition
  v1.5.1 and identifying Journal, Memory Intelligence, and Activation as a
  product relationship that might not have been carried through operationally.
- The exact source is preserved at
  `docs/initiatives/PS-JOURNAL-001/source/PeerSlate_Company_and_Product_Bible_v1.5.1.docx`
  with SHA-256
  `01848a19271942780f740f5220bf48816f664fe134236e28da4a61d49bf3626b`.
- Bible v2.6 already contains much of the conceptual direction. It and Roadmap
  v2.5 remain current authority; `PS-JOURNAL-001` records the precise
  reconciliation and supersedes the earlier operational hold only.
- Journal is the member's private-first memory profile over confirmed canonical
  Moments. It is not a second narrative store. Capture preserves source,
  confirmed Moment preserves member-approved meaning, and Journal presents the
  governed chronological experience over that truth.
- Memory Intelligence is private, source-linked, uncertain, correctable,
  dismissible, exportable, and deletable interpretation. It may never silently
  become a public fact or canonical profile claim.
- Activation is explicit. Use This Moment may propose a reference, placement,
  private draft, reminder, Goal/Project step, or Studio scenario, but may not
  publish, broaden an audience, or copy canonical truth without member action.
- Deep Navy Gold and the approved Journal/My Slate board control the visual
  direction; v1.5.1 Iris styling does not return.
- This decision activates definition and architecture only. No target Journal
  route, schema consumer, UI, feature flag, AI output, audience view, or
  production behavior is implemented by the restart checkpoint.
- The next product gate is a fresh architecture branch that resolves route,
  data, lifecycle, server authorization, visual mapping, migration, rollback,
  and two-member validation before a private owner Journal vertical slice.

## 2026-07-20 - Adopt the connected-system and return-value direction

- Owner decision: PeerSlate does not need more destinations. It needs a stronger
  visible trunk. **Every page should feel like a different use of the same
  life.**
- Adopt Bible v2.7 and Roadmap v2.6, superseding Bible v2.6 and Roadmap v2.5.
  The entire v2.6 constitution is preserved: member-first and private-first
  direction, capture-once/connect-many, one connected Slate, visual-integrity
  covenant, member-directed Story covenant, and the Projects covenant.
- Every major room shall state what it helps the member do, whose space and
  which truth state the viewer is in, where its material came from, how it
  relates to the larger Slate, and one best safe next move.
- Connection is created through canonical references and member-directed
  actions. No room copies another room's authoritative facts, and no generic
  "related content" or promotional rail substitutes for a governed relationship.
- Public and owner modes use the same interaction grammar with different
  server-authorized payloads. Private context is never retrieved and filtered in
  the browser.
- A focused task room is not interrupted. The default connective budget is one
  primary bridge and no more than two secondary paths.
- Return value shall be created through useful memory, preparation, reflection,
  and gentle continuation. Guilt, loss framing, punitive streak recovery, public
  consistency pressure, and popularity manipulation are rejected for the current
  program. Returning after absence is continuation, not failure.
- Voice and text are first-class paths into the same ownership, provenance,
  review, correction, privacy, lifecycle, and activation architecture.
  Voice-derived emotional cues may be humble optional observations only, never
  diagnosis.
- The proof graph is an acceptance outcome of `PS-PLACEMENT-001` and later
  connected-view packages, not a new product, destination, or truth store.
- Preserve Slate Spine, Resume Backstory Drawer, Studio Return Ticket, Then and
  Now, Focus Themes, and Progress Keepsakes as canonical experience patterns
  inside existing rooms. Preservation is not implementation authorization: none
  has a manager, writer, branch, schema, accepted visual authority, or release.
- Register `PS-PUBLIC-CONNECTIVE-001`, `PS-CONNECTIVE-COMPONENT-001`, and
  `PS-RETURN-VALUE-001` as candidate, unassigned packages. The public pilot
  requires an accepted production-intent mockup and an assigned manager and
  writer before any branch. The return-value engine is blocked behind the Owner
  Home frontend and real confirmed history.
- The eleven Open decisions recorded in Bible v2.7 Section 19 remain **open**.
  No implementation assumption may silently close them.
- This decision changes no feature flag, route, schema, deployment, or
  production setting, and enables no gated capability. Owner Home remains
  default-off, Photo Capture remains flag-off, Projects remain planned, and the
  PS-JOURNAL-001 definition/architecture gate is active while the target Journal
  UI remains not live.
