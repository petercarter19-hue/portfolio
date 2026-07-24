# PeerSlate Manager Session Handoff

_Current snapshot: 2026-07-24. Fetch `origin` before relying on any recorded
commit or lane status._

> **Historical reconciliation, 2026-07-21.** A manager session found that Azure PRs 103-110,
> 112-114, 116, 117, and 119 had never been recorded in the controlling
> governance pointers, and that two closed lanes were still described as open.
> See `docs/initiatives/PS-GOV-TRUTH-RECONCILIATION-001/README.md` for the full
> finding and `docs/governance/OPEN_BRANCH_REGISTER.md` for pushed work that
> sits outside every lane record.
> Its branch is no longer local or on Azure and it holds no active reservation.
>
> **Standing instruction for every future manager:** at closeout, update
> `CURRENT_BASELINE.yaml`, `CURRENT_STATE.md`, and
> `ACTIVE_INITIATIVES.md` together only when authority, package ownership/status,
> or verified production truth changed. Otherwise do not create pointer churn:
> the completion report must explicitly affirm that no pointer update was needed.
> A governance release that does rewrite these files must reconcile every merged
> pull request since the last recorded one, not only its own lineage.

## Current authority

- Azure DevOps remote `origin` and `origin/main` are the only source of truth.
  GitHub is a backup mirror and is not a release source.
- `docs/governance/CURRENT_BASELINE.yaml` names the controlling Markdown Bible
  and Roadmap plus their frozen DOCX source snapshots; do not hardcode their versions in this handoff.
- Their Journal-system activation is on authoritative `origin/main` through
  source `578081f5191dd74daa154941604a2b199c5fed58`, Azure PR 118, squash
  merge `3d7c9e10811dcbcc763d965d7770bd0d35e51d4b`, and automatic pipeline 171.
- The current one-Journal decision is controlled by:
  - `docs/initiatives/PS-GOV-JOURNAL-SYSTEM-001/README.md`
  - `docs/initiatives/PS-GOV-JOURNAL-SYSTEM-001/04_ACTIVE_LANE_COMPATIBILITY_AND_TRANSITION.md`
  - `docs/initiatives/PS-JOURNAL-001/README.md`
  - `docs/initiatives/PS-RETURN-VALUE-001/README.md`
  - `docs/initiatives/PS-ASK-SLATE-AI-001/README.md`
  - `docs/initiatives/PS-MESSAGING-001/README.md`
  - `docs/governance/OWNER_STORY_COMPOSITION_STANDARD.md`
  - `docs/governance/EARLY_LEGAL_AND_SITE_READINESS_STANDARD.md`
  - `docs/AI_MODEL_AND_ROLE_ROUTING.md`
- `docs/governance/CURRENT_STATE.md` is the verified product/release snapshot.
  `docs/governance/ACTIVE_INITIATIVES.md` is the lane allocation. This handoff
  does not replace either record.

## Mandatory session start

1. Open and follow `START_HERE.md`.
2. Read `docs/AI_WORKFLOW.md` in full.
3. Inspect branch, status, remotes, worktrees, stashes, and active writers.
4. Fetch and prune `origin`; compare the intended base to current
   `origin/main`.
5. Read `CURRENT_BASELINE.yaml`, `CURRENT_STATE.md`,
   `ACTIVE_INITIATIVES.md`, the exact Bible/Roadmap named there, and the
   assigned initiative package.
6. Confirm exactly one manager, one writer, one task branch, writable files,
   forbidden files, visual authority, and entry/acceptance evidence.
7. Stop if the authority pointer, branch owner, or shared-file reservation is
   unclear. Do not reconstruct a product decision from chat memory.

## Manager and writer model

- The manager is a package-designated role. A ChatGPT Work/Codex manager or
  Claude Co-Work may hold it when the package says so.
- The manager owns sequencing, governance truth, shared-file reservations,
  visual authority, exception escalation, and final manager acceptance.
- The assigned writer owns implementation, complete-diff review, correction,
  tests, evidence, PR readiness, and approved release/closeout.
- One manager does not routinely pay a second model to re-author an accepted
  package. Use `docs/AI_MODEL_AND_ROLE_ROUTING.md`: one manager, one
  self-managed writer, and a fresh independent reviewer only when risk or the
  package requires it.
- Claude Co-Work management is distinct from Claude Code branch ownership.
  Codex or Claude may be a writer only when the package assigns that branch.
- A handoff to another writer requires the exact branch, full pushed SHA,
  status, evidence, open findings, writable/forbidden scope, and explicit
  relinquishment.

## Released and live boundaries to preserve

- The accepted Interview Studio 5A-light/5C-dark implementation released
  through Azure PR 101 at merge
  `39002f5130a1766d2090007c16582e0dbe07226c`; pipeline 149 passed and the
  released assets/live desktop and 390px behavior were verified. PR 102 and
  pipeline 150 closed its governance.
- Private text and Voice Capture are deployed. Speak and Type remain
  first-class. Preserve ownership, source, correction, lifecycle, export,
  deletion, Blob/Speech, and signed-in authorization contracts.
- Canonical Moment confirmation is released through PS-MOMENT-001. The current
  deployed multi-step mechanics are valid implementation history, but they do
  not lock future information architecture or authorize a separate Journal
  truth body.
- The Placement backend is released as an exact-reference foundation. No live
  control is thereby authorized to create a Story, Journal, Work, Project,
  Resume, Feed, Studio, or public projection.
- Capture Photo is released flag-off. Do not enable its source-only journey.
  A later package must integrate universal composer/Save Moment/derived
  Journal behavior or obtain an explicit owner-approved temporary exception,
  in addition to lifecycle, two-owner, homepage-parity, and enablement gates.
- The finite Owner Home backend is released default-off; `/app` remains
  unchanged and the neutral API boundary remains expected until the approved
  frontend/enablement work completes.
- Public typed Ask Pete AI is live against approved public knowledge only. It
  has no private Slate retrieval, upload, OCR, voice, or message authority.
- The public My Story route is a fixed fixture-driven projection. The future
  member Story Composer is planned, not live.

## Active and independently sequenced lanes

| Lane | Current state | Next controlled action |
|---|---|---|
| PS-HOME-INTERVIEW-PARITY-001 | **Closed.** Released by PR 105 at `4deb0a07b6faf2d93d445e212207aeb84b1a71c4`, pipeline 154; closed out by PR 106, pipeline 156; verified live | None. Homepage Interview parity is closed; a further change needs a new package |
| PS-CAPTURE-PHOTO-LIFECYCLE-001 | **Closed.** PRs 107/108/109, pipelines 157/158/160; Photo still flag-off; Defender choice B recorded | Settle the Defender A/B contradiction in the open-branch register before any production proof planning |
| PS-GOV-PAGE-PURPOSE-AI-EVAL-001 | Pete-authorized current ChatGPT Work/Codex governance lane; Codex sole documentation writer; no runtime scope | Complete the documentation-only page-purpose/AI-evaluation/Markdown-authority evidence and handoff; do not claim merge, deployment, enablement, or live behavior |
| PS-HOME-FRONTEND-001 | Exact-authority frontend package activated; separate Codex writer assignment is recorded in current governance | Implement only the finite truthful `owner-home.v1` contract; preserve default-off behavior; treat `/app/capture` only as the recorded temporary bridge, never target IA |
| PS-CAPTURE-MEDIA-001 | Photo is released flag-off; enablement writer unassigned | Keep disabled; later integrate Save Moment/derived Journal or obtain an explicit temporary exception, then pass lifecycle/isolation/homepage-parity/enablement gates |
| PS-JOURNAL-001 | Architecture is current; private-core runtime writer unassigned | Start one fresh branch from post-authority `origin/main` and prove the bounded private core |

These lanes do not share a branch. Shared-governance edits require an explicit
reservation and must be serialized.

## One-Journal constitutional decisions

1. Capture is an action that may open wherever the member is authorized to use
   it. It is not a required page, tab, or destination.
2. The final navigation/route map is still open. Do not lock a permanent mobile
   or desktop navigation set merely to expose Capture.
3. The member-facing commit is **Save Moment**. Opening or dismissing Capture
   does not create a member record.
4. Technical upload, original-source, transcription, revision, processing, and
   AI-proposal states may exist underneath or inline. They are not user-facing
   navigation gates.
5. Save Moment creates one private canonical Moment in member-authored or
   explicitly accepted/reviewed language. AI enrichment may not delay,
   replace, or silently rewrite it.
6. Every eligible saved Moment belongs to that owner's one Journal by
   deterministic derived membership. No Journal Placement, Add to Journal step,
   copied `journal_entry.body`, or second fact store is allowed.
7. The owner Journal is the complete private chronology. Public, Connection,
   and selected-person Journal experiences are separately gated,
   server-authorized, owner-curated projections over the same exact Moments.
8. Authorization occurs before retrieval. Client filtering is never a privacy
   boundary.
9. Journal and My Story remain distinct. Journal is complete, chronological,
   searchable, and lifecycle-oriented. My Story is finite, intentionally
   selected, authored, and visually composed. Both use exact governed Moment
   references.
10. Saving a Moment adds no Story item. Removing a Story item leaves the Moment
    in Journal. Publishing either view is a separate explicit action.
11. Feed, Work, Projects, Board, Resume, Studio, Story, and future messaging
    consume governed references or projections after Save Moment; they do not
    create competing canonical fact pipelines.

## Private Journal implementation entry gate

The next Journal writer must implement only the private core described in
`docs/initiatives/PS-JOURNAL-001/05_IMPLEMENTATION_TEST_AND_RELEASE_SEQUENCE.md`.
Before product edits, the package must name:

- exact current-main base, branch, manager, sole writer, reserved files, and
  forbidden files;
- route and modal/drawer/inline Capture behavior without a Capture destination;
- owner-derived Journal query and deterministic eligibility rules;
- exact Moment/version/lifecycle semantics and no copied body;
- authorization-before-retrieval and two-member isolation;
- private-default audience behavior and later-projection exclusions;
- migration, compatibility, rollback, observability, and failure recovery;
- production-intent desktop/mobile/zoom/keyboard/reduced-motion visual authority;
- focused, full, accessibility, security, lifecycle, and production evidence;
- homepage-impact assessment and named Pete/designated-manager acceptance gate.

Do not include public Journal, replay, Momentum, prompts, observations, Slate
Mirror, Ask Slate AI, messaging, Story Composer, Projects, or navigation lock in
the first private-core implementation unless a later owner decision explicitly
changes the bounded package.

## Planned committed architecture

### PS-RETURN-VALUE-001

- Committed services: replay/resurfacing, Momentum, Prompt/Ritual, What
  PeerSlate Noticed, and Slate Mirror.
- Sequence after the private Journal core. The package may take bounded slices;
  it is not an all-at-once implementation promise.
- Every output is private, source-linked, correctable, dismissible,
  rate-limited, and non-diagnostic.
- Momentum is not necessarily daily. Quiet, purposeful, truthful,
  non-competitive acknowledgements/badges are allowed. No points, levels,
  public rankings, punitive reset/loss state, shame, or trophy spam.
- Life Constellation, synthetic own-voice playback, and other unselected ideas
  remain in `03_REVISIT_REGISTER.md`.

### PS-ASK-SLATE-AI-001 and PS-ASK-PETE-AI-001

- **Ask Slate AI** is the planned signed-in umbrella. **Ask My Slate** is a
  contextual CTA. Interview, qualification alignment, and other specialist
  experiences remain workflows, not separate bots.
- Ashley AI is retired terminology.
- **Ask Pete AI** is Pete's public instance of **Ask [Name] AI**. It retrieves
  only approved public sources.
- Private Type/Speak/file/screenshot/OCR inputs, private Slate retrieval,
  source display, proposals, retention/deletion, and consequential workflows
  belong to Ask Slate and require separate risk gates.

### PS-MESSAGING-001

- Messaging is committed later direction and need not be in the first version.
- No implementation begins without identity, Connection/consent,
  authorization, safety/moderation, mute/block/report, retention/deletion,
  notification, abuse-response, rate-limit, accessibility, and legal gates.
- AI may propose text but cannot address or send a message.

### Early legal and site readiness

- Use `docs/governance/EARLY_LEGAL_AND_SITE_READINESS_STANDARD.md` now to
  inventory Terms, Privacy, cookies/tracking, accessibility, AI disclosures,
  community rules, media/voice, retention/deletion, export, minors/age,
  reporting/moderation, and incident contacts.
- Repository drafting is not legal advice or counsel approval. Counsel and
  security gates precede public Journal, broad community/messaging, private
  multimodal AI, and broad launch claims.

## Story and public-Journal boundary

- A public Journal may eventually feel like a curated profile/timeline, but it
  is not live merely because the owner Journal architecture exists.
- My Story preserves the visual presentation Pete values. The Composer stores
  owner-scoped layout/presentation metadata separately from exact canonical
  Moment references and never creates a second copy of the facts.
- Public Journal and My Story need separate audience, publication, revision,
  preview, accessibility, moderation, failure, and withdrawal evidence.

## Stop conditions

Stop and escalate if any proposed work would:

- write directly to `main`, use GitHub as release authority, or take an active
  writer's branch without exact relinquishment;
- encode Capture as a required destination or add another permanent nav layer;
- create a Journal-entry narrative body or Add to Journal gate;
- retrieve private records before authorization or rely on client filtering;
- silently publish, broaden audience, create a Story item, place a Moment, send
  a message, or apply an AI proposal;
- merge the complete Journal with the finite My Story composition;
- claim planned return, AI, messaging, public Journal, legal, or moderation
  behavior is implemented or live;
- mix Journal, Owner Home, Interview homepage parity, or Capture Photo into one
  writer branch without a new owner-approved package.
- enable Home or Photo while an inherited Capture destination/source-only save
  conflicts with the current transition record.

## First actions for the next manager

1. Fetch `origin` and verify current `main`, authority hashes, pipeline state,
   and the production/auth boundaries relevant to the assigned package.
2. Read the current initiative package end to end and confirm there is no
   active writer conflict.
3. For Journal, assign one manager and one writer to the private core only.
4. Name the production-intent visual authority before user-facing edits.
5. Keep public Journal, My Story Composer, return services, Ask Slate AI, and
   messaging as separate later gates.
6. Require complete-diff self-review, focused/full tests, responsive and
   accessibility evidence, exact branch/SHA, and truthful `Pass`, `Conditional`,
   or `Fail` certification.
7. After Pete/designated-manager acceptance, use Azure PR squash merge, monitor
   the Azure pipeline, verify exact `origin/main`, and record production truth.

## Paste-ready kickoff

> You are the designated PeerSlate package manager or writer named by the active
> initiative. Work only from current Azure `origin/main`. Read `START_HERE.md`,
> `docs/AI_WORKFLOW.md`, `CURRENT_BASELINE.yaml`, `CURRENT_STATE.md`,
> `ACTIVE_INITIATIVES.md`, the exact Bible/Roadmap named there, this handoff, and
> the assigned initiative package before planning or editing. Confirm one
> manager, one writer, branch ownership, reserved and forbidden files, visual
> authority, and entry evidence. For Journal, preserve Capture as an action,
> Save Moment as the one member commit, derived owner-Journal membership, no
> copied Journal body, authorization-before-retrieval, and the distinct My Story
> projection. Implement only the package's bounded slice, self-review the entire
> diff, correct findings, run all required evidence, and return an exact pushed
> branch/SHA with `Pass`, `Conditional`, or `Fail`. Do not claim a planned or
> flag-off capability is live. Merge only through an accepted Azure pull request
> and verify the exact pipeline and production boundary afterward.
