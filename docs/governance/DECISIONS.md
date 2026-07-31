# PeerSlate Manager Decision Log

This is an append-only operational decision record. The current Constitution
and Roadmap named in `CURRENT_BASELINE.yaml` remain the product authority.

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

## 2026-07-20 - Adopt universal Capture, one derived Journal, trusted return services, and bounded AI/messaging architecture

- Adopt Bible v2.8 and Roadmap v2.7, superseding Bible v2.7 and Roadmap v2.6
  wherever they conflict. Preserve the earlier versions as decision history.
- Capture is an action that can open in any authorized context. It is not a
  required page, tab, or destination. The final route/navigation map remains
  open and must be approved separately.
- The member-facing commit is **Save Moment**. Technical source, upload,
  transcription, revision, processing, and proposal states may exist inline or
  underneath, but the action creates one private canonical Moment in
  member-authored or explicitly accepted/reviewed language. AI enrichment may
  not delay, replace, or silently rewrite that commit.
- Every eligible saved Moment belongs to its owner's one Journal by
  deterministic derived membership. Do not create a Journal Placement, Add to
  Journal gate, copied `journal_entry.body`, or second canonical narrative.
- The owner Journal is the complete private chronology. Public, Connection, and
  selected-person Journals are server-authorized, owner-curated projections
  over the same exact Moments and may feel like a timeline/profile. Authorization
  occurs before retrieval.
- Journal and My Story are not merged. Journal is complete, chronological,
  searchable, and lifecycle-oriented; My Story is finite, intentionally
  selected, authored, and visually composed. Both reference exact governed
  Moment versions. Saving a Moment adds no Story item, and removing a Story item
  does not remove the Moment from Journal.
- Downstream Feed, Story, Work, Projects, Board, Resume, Studio, and future
  messaging use exact references and purpose-specific projection metadata after
  Save Moment. No consumer independently creates a competing fact pipeline.
- Commit `PS-RETURN-VALUE-001` as staged future architecture for replay and
  resurfacing, Momentum, Prompt/Ritual, What PeerSlate Noticed, and Slate Mirror.
  Outputs are private, source-linked, correctable, dismissible, rate-limited,
  non-diagnostic, and non-shaming. Momentum is not necessarily daily. Quiet
  acknowledgements or badges may be used for truthful, purposeful,
  non-competitive criteria; points, levels, public rank, loss/reset framing, and
  trophy spam remain rejected.
- The signed-in intelligence umbrella is **Ask Slate AI**. **Ask My Slate** is a
  contextual CTA. Specialist experiences are workflows, not separate bots.
  **Ashley AI** is retired terminology. **Ask Pete AI** remains Pete's public
  instance of reusable **Ask [Name] AI** and cannot retrieve private Slate data.
- Messaging is a committed later direction, not a first-release capability. It
  requires identity, Connection/consent, authorization, safety and moderation,
  blocking/reporting, retention/deletion, notification, abuse response, and
  legal gates. AI may propose wording but never sends a message.
- Original authorized audio playback may remain possible. Synthetic or cloned
  own-voice playback is not committed. Life Constellation and other unselected
  research concepts remain in the Revisit Register.
- Adopt the Early Legal and Site Readiness Standard now. Counsel and security
  gates must precede public Journal, broad community/messaging, private
  multimodal AI, or broad launch claims.
- Adopt the AI Model and Role Routing standard: one durable package manager,
  one self-managed writer, and an independent reviewer only when risk warrants
  it. Do not spend tokens re-authoring an already accepted architecture merely
  to pass it between Claude and Codex.
- This authority package changes no route, schema, feature flag, deployment
  setting, audience, AI service, message path, or live product behavior. The
  next product gate is one bounded private-Journal-core implementation package.

## 2026-07-24 - Adopt lean delivery with risk-based review and periodic audits

- Owner decision: use one pass for each distinct delivery responsibility across
  PeerSlate. Remove duplicated architecture, review, closeout, and
  documentation/release ceremony unless a defined risk, conflicting evidence, or
  material change makes more work necessary.
- Architecture is used only when needed. One writer implements, tests, and
  self-reviews. A fresh independent reviewer is mandatory for architecture-heavy
  work; authentication/session/authorization/privacy/cross-user data; schema or
  migrations; publication/audience/deletion; consequential AI; shared
  infrastructure; conflicting evidence; or an explicit package risk control.
  The same writer corrects accepted findings and reruns affected evidence.
- Pete is the final visual reviewer for material user-facing work and reviews the
  corrected real build. The manager accepts scope/product readiness without
  repeating the writer's full technical audit.
- Retain pre-merge verification, complete-diff self-review, applicable tests,
  runtime pipeline/deploy, live verification, truth/status boundaries, and
  rollback/stop controls. Documentation-only work does not deploy merely to
  record governance.
- Use lightweight quality checks for every runtime slice; checkpoint audits every
  four completed runtime implementation slices or at a major phase boundary;
  readiness audits before default-off enablement or a new public, identity, data,
  or publication boundary; full site audits quarterly or before a major
  launch/public beta; and immediate audits after incidents, regressions,
  cross-user risk, unsafe migrations, conflicting evidence, or a `Conditional`
  or `Fail` result.
- Each audit uses one fresh reviewer in the active ecosystem, exact evidence and
  SHAs, and one compact ranked `Pass`, `Conditional`, or `Fail` report. It
  samples cross-system drift rather than replaying prior reviews and expands only
  on findings.
- Packages use stable role names. `docs/AI_MODEL_AND_ROLE_ROUTING.md` is the
  periodically verified central authority for current model versions and role
  routing. This decision supersedes older package instructions that require
  duplicate model passes or stale hardcoded model versions, except for a
  necessary package-specific risk control that remains explicitly recorded.

## 2026-07-24 - Make ChatGPT the sole visual-authority creation lane

- Owner decision: every new or materially revised PeerSlate production-intent
  visual is created through ChatGPT. This includes concepts, mockups,
  storyboards, responsive and state sets, style exploration, and image
  generation or editing. Authorities Pete locked before this decision remain
  valid until materially revised.
- Pete selects and locks the exact durable visual authority before a writer
  implements it.
- Codex and Claude may implement the locked authority, capture implementation
  evidence, report parity, usability, truth, or accessibility findings, and
  make documented non-material adaptations for semantic structure, focus,
  WCAG contrast, touch targets, reduced motion, truthful state wiring, or text
  reflow. They may not originate or substitute the visual direction.
- The current Codex and Claude architect, implementer, and reviewer choices
  remain centralized in `docs/AI_MODEL_AND_ROLE_ROUTING.md`; this decision does
  not duplicate mutable model versions.
- A change to composition, hierarchy, dominant object/action, typography
  family, color language, or responsive interaction model is material. The
  writer returns that visual decision to ChatGPT, and work resumes after Pete
  locks the revised exact authority.
- Browser screenshots, accessibility evidence, and bounded parity critique are
  implementation/review evidence, not competing visual creation.

## 2026-07-24 - Require page-purpose review and stage the AI quality program

- Before ChatGPT creates or materially revises a production-intent visual, Pete
  approves a page-purpose/non-redundancy inventory for every meaningful visible
  item, card, control, and status. Each retained item names its member purpose,
  source/capability truth, action/destination, privacy/audience/lifecycle,
  unique relationship, and a Keep/Change/Combine/Remove/Defer decision.
  Repeated decoration may group; meaningful product elements may not. Locked
  visuals do not add unlisted meaningful items.
- Build Your Future's future Goal Board is future-facing, private by default,
  and not work history, a Project tracker, or a second truth store. Its category
  contract is Short Term, Long Term, Work, and Custom. The exact future
  Workshop/Goal Board purpose decisions and inventories remain in
  `PS-SLATE-STUDIO-IA-001`; no visual or runtime behavior is approved here.
- `PS-AI-PRODUCT-EVAL-001` is the planned cross-product program for the later
  owner dialogue on good-answer anatomy, What Worked Well, Improve Next Time,
  Improved Draft, natural voice, sources/no-evidence, model/provider
  evaluation, prompts/program architecture, golden cases, privacy/adversarial
  checks, cost/latency, agents/roles, and launch thresholds. It occurs after
  Workshop, Build Your Future, and Projects purpose are settled, before broad
  Ask Slate or advanced coaching implementation. It does not select a permanent
  product model or authorize runtime work.
- Bible v2.9 and Roadmap v2.8 now have verified Markdown as their controlling
  format; their exact DOCX files are frozen owner-approved source snapshots.
  Their semantic versions remain unchanged. The conversion manifest preserves
  source/output hashes and equivalence evidence.
- The unmerged branch `codex/2026-07-24-slate-studio-slice-2-architecture` at
  `f6c2b52763d50d0773f20294acacd8d8165e59da` is preserved/rejected/do-not-merge
  history. It is not current Studio, Workshop, Goal, or implementation
  authority.

### Owner approval follow-through

- Pete approved the Workshop and Build Your Future page-purpose inventories on
  2026-07-24 by instructing the designated manager to complete the next two
  stated steps: merge this governance package and lock the inventories.
- This approval authorizes ChatGPT visual creation within the approved rows. It
  does not select or lock a visual, authorize runtime implementation, activate
  Slice 1, or change the rejected Slice 2 disposition.

## 2026-07-26 - Require continuous approved-mockup fidelity

- Owner decision: whenever PeerSlate work is based on a Pete-approved mockup,
  that exact mockup remains the primary visual authority throughout
  implementation, review, correction, acceptance, and release. It is never
  merely first-pass inspiration.
- Clarification from Pete on the same date: the mandatory autonomous agent
  inspection loop applies when Pete is not personally performing the visual
  inspection. The package must record whether Pete or the assigned writer/agent
  is the visual inspector.
- When Pete is not personally inspecting, the writer reviews the mockup,
  implements a bounded pass, renders the corresponding real state and viewport,
  reviews the mockup again, compares the two, records every visible mismatch,
  refines the implementation, and repeats the cycle without a fixed pass limit
  until exact parity.
- When Pete personally performs the visual inspection, he compares the approved
  mockup with the real renders, directs corrections, decides whether another
  pass is needed, and gives or withholds final visual acceptance. The writer
  implements his corrections and returns updated renders. A duplicate
  autonomous agent inspection or mismatch register is not required unless Pete
  requests or delegates it.
- Implementation screenshots, the current build, framework defaults, writer or
  reviewer taste, passing tests, schedule pressure, resemblance, or a plan to
  polish later cannot replace the authority or close the visual gate.
- Under the agent-run path, a later code, content, asset, or layout change that
  can affect the visible result reopens the same compare-refine loop before
  handoff, acceptance, merge, or release. Under the Pete-run path, it returns to
  Pete's comparison and correction cycle before acceptance.
- Truthful content, semantic structure, focus, contrast, touch targets, reduced
  motion, and responsive reflow remain mandatory. A narrow documented
  adaptation must preserve the locked direction. A material visual change or
  an authority that cannot represent a required truthful, accessible state
  returns through ChatGPT and Pete for a revised exact lock; the writer does not
  improvise a substitute.
- The completion evidence records the authority identity and visual inspector.
  Agent-run inspection records passes by state and viewport, mismatch closure,
  final comparison, and any approved narrow adaptation; an unresolved mismatch
  is `Conditional` or `Fail`, never `Pass`. Pete-run inspection records the
  renders he reviewed, his correction directions, returned refinements, and his
  final visual decision.

## 2026-07-26 - Establish a cross-site responsive architecture and implementation audit

- Owner decision: record a deliberate whole-website responsive review after the
  purposes and intended desktop directions for a named release wave are
  settled. Do not allow each implementation writer to invent tablet and phone
  behavior independently.
- Use the Roadmap-reserved `PS-AUDIT-WEB-001` package rather than creating a
  duplicate audit program.
- Gate R1, Responsive Architecture Lock, reviews and owner-locks the exact
  route/state/viewport manifest, shared-shell and navigation relationships,
  semantic content order, component transformations, tablet/phone
  compositions, short-landscape behavior, and 200-percent reflow before the
  selected wave is considered broadly implementation-ready.
- Gate R2, Responsive Implementation Audit, reviews the exact integrated
  branch or deployed-candidate SHA across the same routes, states, viewports,
  supported themes, and failure/recovery boundaries before a major launch,
  public beta, or other website-wide responsive-completion claim.
- The master gate supplements rather than replaces page-local V0-V4 visual,
  responsive, accessibility, truth, security, and release evidence. Mobile
  work continues during page design and implementation; the later audit
  resolves cross-route contradictions and proves the website behaves as one
  system.
- `PS-SHELL-001` owns accepted shared-shell implementation.
  `PS-AUDIT-WEB-001` owns the cross-route responsive matrix and audit. The
  older approximate 1120-1200-pixel shell estimate is not a binding universal
  width and must be reconciled with the exact Overview and other owner-locked
  measured authorities before shell implementation.
- Gate R2 may satisfy the responsive portion of a checkpoint, phase-boundary,
  or full-site audit only when the exact scope, reviewer, SHA, route/state/
  viewport matrix, evidence, and result are the same and the reuse is recorded.
- This decision establishes planning and review authority only. It changes no
  route, visual asset, runtime code, feature flag, schema, deployment, or live
  production behavior.

## 2026-07-26 - Establish professional Candidate, Launch, Operate, and Retire gates

- Owner decision: implement the professional controls identified by the
  site-delivery review rather than leave them as recommendations.
- Use the Roadmap-reserved `PS-OPS-001` package. Gate Candidate is the immutable
  promotion record consuming completed Gate D evidence; Gate Launch governs
  public beta/broad exposure; Gate F retains deployment and immediate live
  verification; Gate Operate begins after F and supplies later and recurring
  production review; Gate Retire governs safe decommissioning.
- Reuse exact accepted package, legal, responsive, accessibility, performance,
  SEO/content, security, support, recovery, and audit evidence. Do not create a
  second feature lifecycle or rerun work merely to populate another checklist.
- Add a minimal, member-data-free process-liveness endpoint with opaque exact
  build identity, dependency compatibility and compile checks, and bounded
  deadline-based post-deployment public smoke as the first repository
  operational floor.
- The existing direct production deployment cannot support a Candidate `Pass`
  by itself. Without a production-like path or an explicit accepted bounded
  exception, the release decision remains `Not Assessed` or `Fail`.
  Post-deploy smoke improves detection but does not reduce blast radius, prove
  staging, progressive exposure, rollback rehearsal, or public-launch
  readiness.
- Staging/App Service slot creation, Azure environment approvals/checks,
  monitoring/alert configuration, scanning-provider selection, analytics/
  consent, and other external configuration require exact infrastructure or
  product authority and evidence. This repository package does not silently
  provision or claim them.
- Follow-up owner decision, 2026-07-26: Pete selected the recommended
  production-like Candidate path and explicitly delegated its bounded
  implementation to the current manager. Because the production Basic B1 plan
  does not support deployment slots, use a separate `peerslate-candidate` Web
  App with separate configuration and no production secrets, identity trust,
  member data, storage, or provider access. Pete later selected the safer
  separate temporary Basic B1 plan so Candidate load cannot consume production
  compute; remove that plan after verified production release. The pipeline
  limits exposure by using no custom DNS or discovery link, running only the
  exact reserved branch, and stopping the candidate after smoke. Select pinned
  local scanners that do not upload repository source: `pip-audit` for public
  Python dependency advisories and checksum-verified Gitleaks for full
  Git-history secret scanning with redacted reports.
- Follow-up owner decision, 2026-07-27: exact Azure build `256` at
  `1ca3ea6120fc8fcbfeba30137a3bfc94d5508772` passed the immutable artifact,
  dependency/secret scan, full-test, isolated deployment, exact live identity,
  canonical route smoke, and stop controls. Pete separately approved Gate
  Candidate `Pass` after reviewing that evidence. No bootstrap exception was
  used. The exact record is
  `docs/initiatives/PS-OPS-001/CANDIDATE_EVIDENCE_2026-07-27.md`; PR, required
  merge workflow, production Gate F, and immediate live verification are
  authorized but remain separately evidenced.
- `Conditional` requires an explicit bounded exception, owner, expiry,
  compensating control, blast-radius limit, and stop/rollback action. Missing
  mandatory evidence without that accepted exception remains `Not Assessed` or
  `Fail`, never `Pass`.
- Gate Candidate, Gate Launch, Gate Operate, and Gate Retire start `Not
  Assessed`. Authorization to build this repository floor is not acceptance of
  a direct-production exception.
- Emergency Release Mode may shorten sequencing only when delay creates greater
  documented production risk. It preserves mandatory identity, security,
  privacy, authorization, approval, smoke, and rollback controls and requires
  focused retrospective evidence completion within two business days.
- Gate Retire covers member notice/export, retention/deletion/legal hold,
  redirects/indexing, dependency and credential shutdown, monitoring/support
  teardown, restoration window, and final proof. It does not itself authorize
  destructive data deletion.

## 2026-07-31 - Adopt lean risk-based delivery governance

- Owner direction: remove unnecessary blockers, repeated reading, duplicate
  gates, and parallel status records without weakening architecture, privacy,
  security, data integrity, accessibility, or truthful release evidence.
- Constitution v3.0 replaces the v2.9 Bible as concise current constitutional
  authority; Roadmap v3.0 replaces Roadmap v2.8 for current sequence. The older
  documents remain historical evidence, not universal startup reading.
- `CURRENT_BASELINE.yaml` is the single live control plane. `CURRENT_STATE.md`,
  `ACTIVE_INITIATIVES.md`, old handoffs, and audit reports remain provenance
  and are not updated by default.
- Delivery uses Routine, Bounded, and Protected paths. Architecture,
  independent review, specialist standards, Candidate, Launch, Operate,
  Retire, and material visual gates run only when their defined trigger applies.
- The `PS-AI-OPS-CHECKPOINT-001` findings remain open on their three affected
  surfaces. Its global unrelated-runtime hold and automatic four-slice
  stop-the-line cadence are retired.
- Every slice retains one writer, complete-diff self-review, proportionate
  testing, Azure PR/pipeline/live truth when released, and the always-on
  multi-user, privacy, authorization, canonical-data, AI-human-control,
  accessibility, and visual-integrity rules.
