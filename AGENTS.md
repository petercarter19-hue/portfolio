# PeerSlate Repository Instructions

> **MANDATORY PRE-WORK GATE**
> Before any analysis that may lead to a write, code change, migration, deployment, or product decision, open and follow [`START_HERE.md`](START_HERE.md). Synchronize from authoritative `origin/main`, then read `docs/governance/CURRENT_BASELINE.yaml`, `docs/governance/CURRENT_STATE.md`, `docs/governance/ACTIVE_INITIATIVES.md`, the current Bible/Roadmap named there, and your assigned initiative package. Stop rather than guess when any pointer or ownership record is unclear. Every material closeout must use [`docs/templates/OWNER_TECHNICAL_COMPLETION_REPORT.md`](docs/templates/OWNER_TECHNICAL_COMPLETION_REPORT.md).
>
> Authoritative versions are always the ones named in `docs/governance/CURRENT_BASELINE.yaml` (currently Bible v2.8 + Roadmap v2.7).

## Mandatory shared AI and Git workflow

Before planning changes, editing files, or running Git write operations, read `docs/AI_WORKFLOW.md` in full. It is the canonical collaboration workflow for Peter, Codex, Claude, every computer, and every worktree. For model selection and manager/writer/reviewer routing, also read `docs/AI_MODEL_AND_ROLE_ROUTING.md`; model names are operational guidance, not product authority.

Non-negotiable summary:

- `origin` is Azure DevOps and is the only source of truth.
- `github` is a backup mirror only; GitHub Actions deployment stays disabled.
- Never commit or push directly to `main`.
- Create one short-lived `work/YYYY-MM-DD-task-name` branch per task.
- Only one person or AI may actively write to a branch at a time.
- The assigned writer self-manages implementation, complete-diff review,
  correction, tests, evidence, PR readiness, and post-acceptance release/closeout.
- Commit and push before handoff; handoffs require the branch and exact full SHA.
- Merge through an Azure pull request using squash merge, then delete the task branch.
- Never discard unrelated work or perform destructive Git cleanup without a verified recovery reference.
- Never stage or commit machine-local configuration, credentials, or secrets.

If another document contains older Git or deployment instructions, `docs/AI_WORKFLOW.md` controls.

## Project purpose

PeerSlate is a multi-user, evidence-backed professional story and growth platform. It is not a Pete-only portfolio. Pete's content is fixture/demo data only.

## Source of truth

The current authority is the Bible, Roadmap, Sync Standard, and design baseline
named in `docs/governance/CURRENT_BASELINE.yaml` (Bible v2.8 + Roadmap v2.7 as of
2026-07-20). `docs/governance/DOCUMENT_CONTROL.md` defines the authority order.
Older v1.1-v1.4 documents and Direction C / Iris-era specifications are retained
as decision history or supporting detail only. Where they conflict with the
current baseline, the current baseline wins and the conflict must be reported
rather than implemented.

**One-Journal system (owner decision 2026-07-20):** Capture is an action that
may be offered in any authorized context; it is not a required page, tab, or
destination. The member-facing commit is **Save Moment**. One saved private
canonical Moment becomes part of that owner's Journal by deterministic derived
membership, without an Add to Journal gate or copied Journal body. The owner
Journal is the complete private chronology. Public, Connection, and selected-
person Journal views are server-authorized projections over those same Moments.
My Story remains a finite, member-authored visual composition referencing exact
Moment versions; it is not a duplicate Journal. Return services and Slate
Mirror/What PeerSlate Noticed must be private, source-linked, correctable, and
member-controlled. Product code remains gated by
`docs/initiatives/PS-JOURNAL-001/README.md`. Do not infer that a target Journal,
public Journal, Ask Slate AI, return-value service, or messaging runtime is live.

**Portable manager assignment (owner decisions through 2026-07-19):** the
manager is a package-designated role, not a single tool. A ChatGPT Work/Codex
manager session or Claude Co-Work may own package sequencing, governance truth,
shared-file reservations, visual authority, exception escalation, and final
manager acceptance. Each package names exactly one current manager. ChatGPT
Codex and Claude Code remain implementation writers only when assigned that
role; Claude Co-Work management is distinct from Claude Code branch ownership.
Writers use separate task branches and self-manage implementation, self-review,
evidence, PR readiness, and approved release/closeout under
`docs/AI_WORKFLOW.md`. The designated manager does not routinely repeat a
coherent self-certified technical audit.

Before changing résumé or Slate Board code, read these repository documents in this order:

1. `docs/peerslate/PeerSlate_Design_Bible_v0.3.md`
2. `docs/peerslate/PS-FEAT-001_Living_Resume_Voice_Blueprint.md`
3. `docs/peerslate/PeerSlate_Product_Backlog.md`
4. `docs/peerslate/PS-EXP-002_Slate_Focus_Stage_Experiment.md`

If any source document is missing, stop and report the missing path. Do not reconstruct requirements from memory.

## Approved design foundation

- **Deep Navy Gold** is the approved shared light-theme system
  (PS-BRAND-NAV-002, 2026-07-17), replacing Iris Foundry and the earlier
  Foundation C indigo. One authoritative navy + marigold system applied
  consistently across every room.
- Newsreader is for cinematic/editorial headings.
- Inter is for navigation, controls, forms, metadata, and product content.
- Light-first, cinematic, premium glass UI.
- Cloud White canvas `#F6F7FA`, surface `#FFFFFF`
- Ink Navy text `#141A28`
- Primary Navy `#203767` (strong `#132447`) — primary actions, headings, active/selected
- Marigold `#B87900` (text-safe `#8A5A00`, soft `#F4E4B4`) — evidence chips, progress, gold highlights
- Success Teal `#1E725F`
- Pink, rose, magenta, coral, and purple/iris are not semantic UI accents.
- Use generous vertical spacing and progressive disclosure. Do not force the experience above the fold.
- One dominant product object per opening viewport.
- Never use the retired résumé example. Never use the MICAP example in redesigned résumé fixtures or visible copy.

## Visual integrity and owner acceptance

- Read and follow `docs/governance/OWNER_VISUAL_INTEGRITY_STANDARD.md` for every
  user-facing design or implementation package.
- An owner-approved production-intent mockup, storyboard, walkthrough, or
  demonstration is a binding visual promise. The real product must be
  recognizably the same interaction model and match or exceed its hierarchy,
  composition, clarity, finish, and professional polish.
- Clearly label what a demonstration simulates and what behavior is live,
  stored, transmitted, local-only, private, public, or future. Truthful labels
  do not make the visual promise optional.
- A technical or functional pass is not visual completion. Material user-facing
  work requires named comparison screenshots and explicit designated session
  manager plus Pete visual acceptance before merge unless Pete delegates that
  gate in writing.
- Do not release a visibly downgraded "function now, polish later" public or
  member experience. A clearly labeled internal preview requires Pete's explicit
  approval and must remain In Progress.
- When a package approves multiple input paths, such as Speak and Type, keep
  them first-class unless the approved authority expressly says otherwise.
- Every user-facing package must record whether the logged-out homepage has a
  section, walkthrough, or product card for that experience. When the real
  product changes materially in function, hierarchy, theme, or visual quality,
  the linked homepage projection must receive a formal parity review and an
  update in the same release wave or an explicitly sequenced downstream package.
- The real product is upstream authority. Homepage sections must be truthful,
  current, product-specific, and independently showcase-quality; they may
  distill the experience for visitors, but may not remain a stale or generic
  version of the product they link to.

## Multi-user and trust rules

- Components must work for students, early-career users, career changers, freelancers, mid-career users, and senior users.
- Never hardcode Pete's employers, dates, role count, metrics, education, or skills into reusable components.
- Every profile-owned record must preserve tenant ownership.
- Default new Board content and voice-created drafts to private.
- AI output is a proposal, not an automatic edit.
- Type and Speak use the same Save Moment contract. Retained voice preserves
  the authorized source and editable transcript, with applicable correction
  inline. Optional structured or AI proposals remain separate and may not
  delay, replace, or silently rewrite the member-saved canonical Moment.
  Publishing is a separate explicit action.
- Never imply production privacy, matching, verification, or AI behavior unless the backend enforces it.

## Living Résumé direction — PS-FEAT-001

- The Living Résumé Ledger appears first.
- Its chronological timeline is integrated into the résumé and acts as its navigation and structural spine.
- Selecting a timeline chapter updates detail inside the same dominant résumé frame.
- The Career Constellation materializes below the Ledger during vertical scroll.
- Skills stay compact and reveal only two or three strongest approved proof points.
- Ledger and Constellation render from the same structured data.
- Keep a traditional ATS-friendly PDF/download path.
- Build with generic data/view models and multiple fixture profiles.

## Slate Board direction

- The whiteboard remains the dominant product experience.
- Preserve its playful, hand-placed quality; do not turn it into a conventional dashboard or card grid.
- Four primary scrollable sections for the first implementation:
  - Short Term
  - Projects
  - Long Term
  - Work
- Sticky notes are the primary board objects.
- Add/Edit supports:
  - To Do, Short Term, Long Term, Project, Work, or Custom
  - sticky-note color
  - cursive or standard handwriting
  - dates
  - privacy/audience
- Keep visible controls concise:
  - Add to Board
  - AI Help
  - Connections
  - quiet More/Board Settings
- Item controls appear contextually, not permanently.
- First interaction fixture: “Study for the PMP certification.”
- Add-to-Board states:
  1. Capture
  2. Details and privacy
  3. Note added
  4. AI guidance
  5. People matching
- Similar-user matching is opt-in and visibility-aware. Never auto-connect users.
- AI may propose milestones, questions, reminders, websites, and videos, but does not save automatically.
- Supporting experiences continue vertically below the opening board. Do not pack everything into one screen.
- PS-EXP-002 Focus Stage remains separate, optional, feature-flagged, and off by default. It must never replace the Board.

## My Story composition direction

- Read `docs/governance/OWNER_STORY_COMPOSITION_STANDARD.md` before any Story
  design, schema, editor, projection, or public-rendering work.
- Story is a member-curated projection from canonical records. Layout metadata
  must remain separate from authoritative Story content and must never create a
  second copy of the facts.
- The future authenticated Story Composer must let members move and resize
  supported notes, text, images, and media; control overlap/layering; undo,
  preview, save a private draft, and publish separately.
- Dragging is not the only interaction. Provide keyboard and structured-editor
  equivalents, stable semantic reading order, mobile reflow, 200% zoom, touch,
  reduced-motion, long-content, missing-media, and failure states.
- AI may propose a layout but may not silently apply, save, overwrite, or
  publish it. The member remains the authority over composition and audience.
- `PS-STORY-COMPOSER-001` is reserved future work, not an active package. Do not
  modify the current public My Story fixture under this direction-only package.

## Universal Capture and the one Journal direction — PS-JOURNAL-001

Read `docs/initiatives/PS-JOURNAL-001/` (README + docs 01–06) before any Capture,
Moment, Journal, projection, audience, or route work. Owner-clarified emphasis
(Pete, 2026-07-21):

- **Capture is an in-context action, not a place.** Eligible signed-in rooms open
  the same universal composer as a pop-out sheet/drawer/dialog over the current
  page. It preserves the origin context and, when the member is done, returns
  them to that exact page. There is no Capture page, tab, or permanent
  destination.
- **Save Moment always creates one private canonical Moment** in the member's own
  authored or explicitly reviewed words. Journal membership is derived
  automatically — there is no Add to Journal step, and the save never depends on
  the member choosing a destination.
- **Catch the moment: in the same breath after Save Moment, the composer offers
  first-class `Use This Moment` options** — share to Feed, add to My Story, use in
  Work or Résumé, and other authorized destinations — together with an audience
  choice. Filing a Moment away silently risks it being forgotten, so these
  options are part of the moment, not buried in the Journal later (they remain
  available from the Journal anytime too).
- **Every share/audience choice is explicit and previewed; nothing is automatic.**
  New Moments default to Only Me. No share, publication, Feed post, or audience
  change is ever bundled into Save Moment or applied silently; each requires an
  exact-audience preview appropriate to its destination before it goes.
- **Sharing is a reference, not a copy.** A placement/projection points at the
  exact canonical Moment version; the Journal Moment stays the single source of
  truth. Removing a projection never removes the Moment from the Journal.
- **Type and Speak are equal**, and essential capture/Journal work must survive
  when AI, speech, or media providers are unavailable.
- **Destinations light up in stages.** Private capture + one Save Moment + the
  derived private Journal ship first (Slice J1). The full `Use This Moment`
  destination chooser and audience projections follow (Slice J2+). Design the
  composer's saved state with the share and audience options from the first
  visual round even though the buttons enable in waves; do not lock a permanent
  navigation set without the route-map gate.

## Projects future direction

- Read `docs/initiatives/PS-PROJECTS-001/README.md` before any Project product,
  schema, workspace, projection, migration, or public-route work.
- A Project is a private-first member-owned container that links exact governed
  records and relationships. Do not copy canonical Moment, source, role,
  outcome, Story, resume, or publication content into Project relationships.
- Keep the authenticated Project Workspace separate from any purpose- and
  audience-specific Project Projection. Completing or editing a Project does
  not publish it.
- Work is the broader roles-and-contributions domain. Slate Board Project notes
  are planning objects, not canonical Projects, and may not create one silently.
- AI may propose Project structure, relationships, reflection, or wording, but
  deterministic software and explicit member actions control lifecycle,
  audience, sharing, publication, archive, deletion, and collaboration.
- PeerSlate Projects must not become a Jira/Trello-style task manager or revive
  the retired Pete-only Projects fixture as the product system of record.
- `PS-PROJECTS-001` is planned Phase 10 work, not an active implementation
  package. Current Project redirects, fixtures, schema, and production behavior
  remain unchanged until the package's full entry gate is approved.

## Navigation

Do not add another permanent navigation layer inside Slate Board. Global site navigation, public/member Slate navigation, and contextual Board controls must remain distinct. Do not finalize or replace production navigation without an approved route map.

## Safe implementation workflow

- The user grants standing authorization for normal project work: creating task branches, committing, pushing task branches to Azure, creating and completing Azure pull requests, configuring Azure DevOps, deploying through Azure Pipelines, and verifying production behavior. This is not authorization to push directly to `main`, rewrite shared history, or bypass `docs/AI_WORKFLOW.md`.
- Azure DevOps is the source of truth. The remote is named `origin`. GitHub is the `github` mirror and must not deploy the application.
- Preserve current pages and behavior where practical, but make the requested changes and resolve implementation blockers autonomously.
- For an assigned self-managed package, perform a distinct complete-diff review,
  fix discovered issues, run all required evidence, and return a `Pass`,
  `Conditional`, or `Fail` self-certification. Do not label unresolved failures
  as passed. After Pete/designated-session-manager acceptance, the same writer may complete
  the Azure PR, pipeline, production verification, and package closeout.
- Prefer reviewable commits and report material changes, but do not treat a dirty worktree or an ambiguous base as an automatic stop condition; inspect it, protect unrelated work, and proceed with the safest reasonable path.
- Do not perform database migrations or add production dependencies without explaining the reason and impact first.
- **Credentials are off-limits:** never request, read, expose, copy, store, commit, rotate, or transmit the user's API keys, passwords, tokens, publish profiles, certificates, or other secrets. Use already-configured secure Azure/Azure DevOps service connections when available; otherwise ask the user to complete the credential-only step themselves.

## Quality requirements

- WCAG 2.2 AA target.
- Keyboard access, visible focus, 200% zoom, high contrast, and reduced motion.
- Slate Board requires an accessible structured/list alternative.
- Mobile uses readable document flow; never shrink a desktop visualization until it is unreadable.
- Prefer transforms and opacity for motion.
- Run the existing test/lint/format commands discovered in the repository.
- Add focused tests for new routes, rendering states, and interactions.
- Capture desktop and mobile screenshots for review.
- Compare user-facing implementation screenshots against the package's named
  visual authority and record every approved deviation.
- Report changed files, commits, commands run, failures, assumptions, and remaining work.

## Communication

Explain architecture and tradeoffs in plain English. Separate:
- what is implemented,
- what is fixture-only,
- what requires backend/schema work,
- what is intentionally deferred.
