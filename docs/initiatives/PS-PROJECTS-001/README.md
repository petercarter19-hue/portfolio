# PS-PROJECTS-001 - Projects Workspace and Project Projections

## Package status

- Status: **Planned - not active**
- Roadmap placement: Phase 10, Moment Lab, Story, Work, and connected views
- Designated session manager for direction registration: Codex manager session
- Future implementation manager: Unassigned
- Implementation writer: Unassigned
- Branch owner for direction registration: Codex on
  `work/2026-07-19-projects-future-architecture`
- Base: `origin/main` at
  `6d5ef46ce05bd7c3a3f6e4b4c356bdf9c9bc6fcd`
- Migration owner: Unassigned; this direction package authorizes no migration
- Visual authority: **Not Started**. The retired public Projects exhibition is
  historical design evidence, not current implementation authority.
- Homepage product projection: no dedicated Projects product section or
  canonical Projects link exists on `/` today; future impact is **Not Started**
- Release boundary: documentation, architecture direction, and governance only

## Owner decision

Pete directed PeerSlate to preserve Projects as a real future product
extension. This is later expansion, not early-release work and not permission to
interrupt the active Interview Studio or Capture Media lanes.

The decision creates a durable Projects system in the product constitution and
architecture. It does not revive the retired Pete-only `/projects` page, turn
Slate Board's Projects column into the system of record, or authorize a project
management clone.

## Product purpose

A Project is a member-owned, private-first container for a meaningful endeavor
that unfolds across time. It connects confirmed Moments, roles, contributions,
decisions, milestones, outcomes, people, goals, skills in practice, sources,
and approved media without copying their authoritative content.

Projects help a member answer four questions:

1. What are we trying to do, and why does it matter?
2. What happened while the work was moving?
3. What did I contribute, decide, learn, and produce?
4. What, if anything, do I want another person to see?

The owner workspace is the private record. A Project Projection is a separate,
purpose- and audience-specific presentation such as a case study, progress
brief, portfolio story, manager update, or selected public Project page.

## Constitutional boundaries

- **Private first.** A new Project and every linked draft begins owner-only.
- **One truth, many views.** Project surfaces use references to canonical
  records and exact approved versions; they do not fork Moment text, dates,
  outcomes, sources, or member identity.
- **Project status is member authority.** AI may suggest a title, relationship,
  summary, milestone, missing context, or next question. It may not create,
  change status, complete, share, publish, archive, or delete a Project without
  explicit member action.
- **Workspace and projection are different objects.** Editing the private
  workspace does not automatically change an audience-visible Project
  Projection. Publication pins the exact approved content and projection
  revision the member previewed.
- **Projects are not a task-management suite.** PeerSlate may remember and
  explain project work, but it is not Jira, Trello, Microsoft Project, a
  timesheet, procurement system, or enterprise delivery system.
- **Projects are not a card grid.** Cards may summarize Projects, but the
  durable product object is the connected Project record and its history.
- **Work remains the broader domain.** Work connects roles, organizations,
  contributions, and outcomes. A Project can sit within one role, span several
  roles, or represent independent, learning, community, creative, or personal
  build work when the member chooses to connect it to professional growth.
- **Slate Board is a planning view.** A Board note may point to or propose a
  Project, but a note is not the canonical Project and cannot create one
  silently.

## Honest current production baseline

- `GET /projects`, `/petec/projects`, `/work`, and `/petec/work` currently
  redirect to `/petec/resume#experience`.
- Historical profile-scoped Project fixtures and case-study data are preserved,
  but their standalone pages are retired.
- Slate Board has a browser-facing Projects column, but it is not an
  authenticated canonical Projects workspace.
- The released Placement foundation can reference one exact confirmed Moment
  version to an existing private/unpublished Slate entity. No website control
  creates or displays Project placements yet.
- No authenticated Project create/edit route, Project schema, Project service,
  collaboration model, audience preview, publication flow, or Project-specific
  homepage section is implemented, deployed, or live.

## Planned product structure

### 1. Private Project Workspace

The owner creates or confirms a Project, sets a small amount of durable context,
and connects existing canonical material. The opening view is a Project Ledger:
purpose and status first, then recent movement, decisions, milestones/outcomes,
linked Moments and sources, and one safe next action.

### 2. Project updates through the existing loop

Capture remains the common input. A member may capture a project update without
choosing a destination first, confirm it as a Moment, then explicitly place or
link that exact confirmed version to a Project. The Project does not copy the
Moment's text.

### 3. Project reflection and reuse

The member can review a period or closing state, identify decisions and
outcomes, fill missing context, and deliberately reuse approved Project context
in Work, Story, Living Resume, Interview Studio/Moment Lab, Replay, or an
export. Every reuse remains source-linked and reviewable.

### 4. Optional Project Projection

A separate later slice lets the member select, order, and word approved Project
material for a named audience and purpose. Exact audience preview, responsive
presentation, private-draft save, explicit publication, revocation, and source
change behavior are mandatory. A projection may be public, connection-only,
selected-person, or private; the private workspace never becomes public by
implication.

## First implementation boundary

The recommended first vertical slice is **owner-only Project foundation and
workspace**:

1. create one private Project with title, purpose, type, status, dates, and
   optional role/goal relationship;
2. register it as an owner-scoped Project destination in the existing Slate
   entity model;
3. explicitly attach one or more already-confirmed Moment versions using the
   released Placement contract;
4. show the Project Ledger from joined canonical references;
5. edit Project metadata with optimistic concurrency;
6. pause, complete, archive, restore, and delete/revoke according to an approved
   lifecycle contract; and
7. prove two-owner isolation and no publication.

The first slice does not include public Project pages, collaborative editing,
comments, Feed distribution, AI-authored project content, task boards,
timesheets, external repository sync, or automatic Project creation from Slate
Board or Capture.

## Docket phases

### Phase A - Product and information-architecture validation

Validate the Project/Work/Slate Board boundaries, primary jobs to be done,
Project types, lifecycle language, one dominant Project Workspace composition,
and the first real Pete/Danielle validation examples.

### Phase B - Experience and visual authority

Produce the complete Project Workspace journey and states under Deep Navy Gold:
desktop workshop, mobile ledger, 200-percent reflow, keyboard, screen reader,
reduced motion, empty, long-content, missing-source, stale edit, restricted,
archive/delete, and recovery. Select and approve one named production-intent
visual authority under `OWNER_VISUAL_INTEGRITY_STANDARD.md`.

### Phase C - Requirements and architecture baseline

Finalize the Project schema, Slate entity registration, Placement consumption,
authorization, lifecycle, concurrency, export/delete propagation, telemetry,
migration, rollback, API, and traceability contracts. Prove that no canonical
Moment or source text is copied.

### Phase D - Owner-only vertical slice

Assign one writer and fresh branch. Implement the bounded Project foundation
and workspace, self-review the complete diff, and obtain technical, visual, and
owner acceptance before Azure release.

### Phase E - Connected reuse and Project Projection

After the private workspace is accepted and live, separately authorize
Project-to-Work/Story/Resume/Studio reuse and the audience-specific Project
Projection. Assess and sequence any homepage projection only after the real
Project product is accepted and live.

## Entry gate before implementation

Implementation remains blocked until all of the following are durable:

- one approved primary member scenario and first-slice Project type set;
- approved Work, Project, Slate Board note, Moment, Placement, and Projection
  boundaries;
- named visual authority with complete V0/V1 states and Pete/manager approval;
- final requirements and architecture allocation, including exact schema and
  migration/rollback ownership;
- proof that the released Moment and Placement contracts can be reused without
  authoritative-text duplication;
- authenticated owner route and viewer/audience boundary;
- two-owner negative-test and data-rights plan;
- homepage-impact assessment and any exact downstream parity package;
- assigned manager, writer, branch, writable files, and migration owner; and
- Pete's explicit authorization to start the implementation slice.

## Reserved files for this direction-registration slice

- `docs/initiatives/PS-PROJECTS-001/**`
- `docs/governance/PeerSlate_Company_and_Product_Bible_v2.6.docx`
- `docs/governance/PeerSlate_Product_Strategy_and_Architecture_Roadmap_v2.5.docx`
- `docs/governance/CURRENT_BASELINE.yaml`
- `docs/governance/CURRENT_STATE.md`
- `docs/governance/ACTIVE_INITIATIVES.md`
- `docs/governance/DECISIONS.md`
- `docs/governance/DOCUMENT_CONTROL.md`
- `docs/governance/MANAGER_SESSION_HANDOFF.md`
- `docs/peerslate/PeerSlate_Product_Backlog.md`
- `docs/PEERSLATE_SITE_RULES.md`
- `AGENTS.md`, `CLAUDE.md`, and focused governance guardrails

No route, template, JavaScript, stylesheet, current Project fixture, résumé
data, Slate Board behavior, service, SQL migration, infrastructure, dependency,
or production capability is reserved or changed.

## Required package records

- [Requirements](01_REQUIREMENTS.md)
- [Experience and visual direction](02_EXPERIENCE_AND_VISUAL_DIRECTION.md)
- [Architecture and data](03_ARCHITECTURE_AND_DATA.md)
- [Traceability and slice plan](04_TRACEABILITY_AND_SLICE_PLAN.md)
- [Test, validation, and release plan](05_TEST_VALIDATION_RELEASE_PLAN.md)
- [Completion report](COMPLETION_REPORT.md)

## Next action

Keep `PS-PROJECTS-001` planned while the current Interview Studio and Capture
Media gates proceed. When Pete chooses Projects as the next Phase 10 slice,
start Phase A/B product and visual validation; do not assign an implementation
writer from this governance package alone.
