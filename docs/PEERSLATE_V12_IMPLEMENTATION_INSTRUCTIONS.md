# PeerSlate Claude Implementation Instructions

**Instruction version:** 1.0  
**Product baseline:** PeerSlate Company & Product Bible, Foundation Edition v1.2  
**Decision date:** July 16, 2026  
**Owner:** Peter Carter  
**Authoritative repository:** Azure DevOps `origin`; `origin/main` is production  
**Production deployment:** Azure Pipelines only

## Purpose

These instructions convert the approved PeerSlate product decisions into an implementation program. They are not permission to rebuild the application in one branch. Work in small vertical slices, inspect the repository first, preserve existing production behavior, and stop when a requested slice depends on an unapproved architecture or missing prerequisite.

Read these files completely before planning any change:

1. `PeerSlate_Company_and_Product_Bible_v1.2.docx`
2. `PEERSLATE_SITE_RULES.md`
3. All repository-local instructions, including the existing `CLAUDE.md`, `AGENTS.md`, `README`, deployment documentation, and initiative folders
4. The current implementation for the routes, templates, services, SQL access, authentication, storage, AI, and tests touched by the package

The Bible governs product direction. The repository governs the current implementation. When they conflict, report the conflict before changing code.

---

# 1. Non-negotiable product interpretation

PeerSlate is a private-first, voice-first, AI-enabled living Journal for work and life. It helps a member capture real moments, understand them, connect them to the rest of the member's Slate, and deliberately choose what to keep private or share.

The primary product is not a public profile, recruiter utility, resume PDF, job board, or social feed. The owner loop is the product center:

> Capture something real -> let PeerSlate understand it -> review it -> keep it private or share it -> receive more value from it later.

The canonical system rule is:

> Enter once. Link everywhere. Publish deliberately.

Do not create duplicate sources of truth for Journal, Feed, Story, Work, Resume, Projects, Slate Board, Career Constellation, or Interview Studio.

## Locked decisions

- Iris Foundry is the shared color system.
- Journal is the displayed product term and the canonical member timeline.
- Evidence is removed as a top-level destination and repeated user-facing label.
- Internal source, provenance, support, and audit relationships remain intact.
- The Community desktop right rail contains one Note card only.
- A quiet rotating AI Journal check-in lives inside that Note card; it is not another dashboard widget.
- Replace the single generic Encourage action with a purposeful Respond system.
- Projects, achievements, and promotions belong on Career Constellation.
- Resume Creator is an owner feature inside Work; the PDF is a generated export, not the source of truth.
- A member may upload an external job description for private Qualification Alignment.
- Qualification Alignment is based on explicit basic and preferred qualifications, not generic skills or keyword similarity.
- PeerSlate never hosts, posts, recommends, indexes, sponsors, or syndicates job listings.
- Polls are never filler. Do not seed or auto-generate them to decorate Community.
- Interview Studio must clearly separate generic best-practice examples from answers grounded in the member's history.
- When relevant member history is missing, AI asks a focused question and offers to add the answer as a private draft.
- About PeerSlate does not belong in signed-in product navigation or public member navigation.
- No member-specific public AI assistant appears inside Community.
- No public follower-count or reaction-count status economy.

---

# 2. Required delivery method

## One package at a time

Do not implement all packages in this document at once. Each package requires its own initiative folder, plan, branch, review, verification, and handoff.

Use the repository's established naming if it already exists. Otherwise use:

```text
docs/initiatives/<PACKAGE-ID>/
  README.md
  01-requirements.md
  02-current-state.md
  03-architecture.md
  04-data-model.md
  05-security-privacy.md
  06-test-plan.md
  07-implementation-plan.md
  08-decisions.md
  09-verification.md
  10-handoff.md
```

Suggested branch format:

```text
claude/<package-id-lowercase>-short-name
```

## Mandatory inspect-first phase

Before code or configuration changes:

1. Report the current branch, SHA, status, remotes, worktrees, and stashes.
2. Confirm that `origin` is Azure DevOps and identify the production branch and pipeline.
3. Inventory the relevant routes, templates, components, static assets, API endpoints, services, SQL queries, migrations, environment variables, feature flags, tests, and mocked behavior.
4. Identify whether authentication and trusted server-side identity already exist.
5. Identify all current data stores and whether the page is fixture-driven, database-backed, or mixed.
6. Map ownership and visibility for every record the package will read or write.
7. Record existing defects that are in scope and unrelated issues that must not be changed.
8. Produce `02-current-state.md` and `07-implementation-plan.md`.
9. Do not install packages, alter Azure resources, run destructive migrations, or edit code until the plan is approved.

## Definition of done for every package

A package is complete only when it includes:

- Real owner-aware behavior, not Pete-only fixture logic
- Forward and rollback database migration where data changes are required
- Server-side authorization and cross-user isolation
- Private-by-default records and explicit publication behavior
- Loading, empty, error, retry, unavailable, and permission-denied states
- Keyboard, screen-reader, reduced-motion, 200% zoom, mobile, and long-content checks
- Automated unit and integration tests for the accepted scope
- Privacy-safe logs and useful operational metrics
- No exposed secrets or private content in client-side state or logs
- Verification commands and results in `09-verification.md`
- Exact statement of what is working, mocked, deferred, or known-broken in `10-handoff.md`
- Staging validation with separate Pete and Danielle accounts when the package is user-facing

---

# 3. Approved implementation order

The order below reflects current product priority. Do not skip prerequisites silently.

1. `PS-PLAN-002` - Current-state audit and v1.2 decision reconciliation
2. `PS-RULES-001` - Repository rules and product guardrails
3. `PS-INTERVIEW-002` - Interview mode clarity, follow-ups, and history capture
4. `PS-BRAND-NAV-001` - Iris Foundry, navigation cleanup, and About repositioning
5. `PS-JOURNAL-002` - Journal center, Note card, and rotating AI Journal check-in
6. `PS-FEED-002` - Community Feed layout and purposeful Respond system
7. `PS-QUALIFY-001` - Job-description upload and Qualification Alignment
8. `PS-RESUME-001` - Resume Creator and governed PDF/DOCX export
9. `PS-CONSTELLATION-001` - Projects, achievements, and promotions on Career Constellation

Authentication, owner isolation, private storage, universal Capture, and Journal persistence from the v1.1 program remain prerequisites. If the repository does not yet have them, report the dependency and execute the prerequisite package before building a feature shell that cannot be secure or real.

---

# 4. PS-PLAN-002 - Current-state audit and v1.2 reconciliation

## Member problem

The visual site contains strong prototypes, but product language, routes, mocked behavior, owner state, and the v1.2 decisions may be inconsistent. Coding without a map risks preserving duplicate systems and implementing the wrong product center.

## Required output

Create a read-only current-state report covering:

- Full route map for logged-out marketing, signed-in owner, public member, Community, Work/Resume, AI, and Interview Studio
- Top and secondary navigation by route and viewer mode
- Every occurrence of the user-facing terms `Evidence`, `Evidence-backed`, `Proof`, `Feed Preview`, `About PeerSlate`, `Encourage`, and job-related content
- Every Community side module and whether it is real, fixture-driven, or decorative
- Journal data model, publication path, Feed data model, and whether posts are duplicated
- Resume PDF generation/download behavior
- Career Constellation data source and supported node types
- Interview Me, Interview AI, Video Me, feedback, history, scoring, and model-answer behavior
- Ask Pete AI upload capabilities, file processing, retrieval scope, and public/private source boundary
- Existing polling, job/news, challenge, quote, recommendation, following, comment, and post behavior
- Current color tokens and page-specific overrides
- Authentication, owner isolation, storage, migrations, AI provider, and test maturity

## Required diagrams

- Owner/public/connection/logged-out route and permission diagram
- Capture -> Journal -> publication -> Feed projection diagram
- Document upload -> processing -> source -> AI retrieval diagram
- Interview question -> answer -> feedback -> follow-up -> history proposal diagram
- Resume Creator/Career Constellation conceptual data relationship diagram

## Acceptance gate

No production behavior changes. The owner approves a prioritized gap list and confirms which prerequisites are real before implementation begins.

---

# 5. PS-RULES-001 - Repository rules and product guardrails

## Required implementation

1. Add `docs/PEERSLATE_SITE_RULES.md` using the approved rules document.
2. Add or update the root `CLAUDE.md` so it points to the Bible and site rules before any product work.
3. Add a lightweight pull-request or initiative checklist covering:
   - canonical object affected
   - owner and audience
   - private/public behavior
   - AI vs deterministic responsibility
   - source/provenance behavior
   - accessibility
   - tests
   - export/delete behavior
   - status truthfulness
4. Add automated static checks where practical for:
   - hardcoded Pete/Danielle IDs in reusable application code
   - forbidden production deployment through GitHub Actions if that is still repository policy
   - accidental client-side exposure of known secret variable names
   - newly introduced `Evidence` navigation labels
   - newly introduced job-listing routes/modules
5. Do not build a brittle word-ban system that blocks legitimate internal migration or documentation references. The checks should target UI/navigation and production behavior.

## Acceptance gate

A new agent or contributor can enter the repository, find the authoritative rules, understand the deployment path, and identify the non-negotiable product boundaries before editing code.

---

# 6. PS-INTERVIEW-002 - Fix Interview Studio now

This is the first user-facing implementation package in v1.2.

## Product behavior

### Interview Me

- The member answers a question by typing or voice.
- PeerSlate evaluates the answer against a visible rubric.
- Preserve the original answer.
- AI feedback is a separate draft and does not overwrite the original.
- Feedback sections:
  1. What worked
  2. Improve next
  3. Follow-up question
  4. Relevant history you may have missed
- The follow-up question adapts to the missing or weak part of the answer: situation, task, action, result, judgment, conflict, ownership, metric, lesson, or role relevance.
- “Relevant history you may have missed” retrieves confirmed, permitted history that may strengthen the answer. It does not use the label Evidence or Proof.
- Actions after feedback:
  - Answer follow-up
  - Improve this answer
  - Try again
  - Save as interview story
  - Add missing history

### Interview AI

Provide a clear segmented control at the top of the answer area:

```text
Best-practice example | Use my history | Compare
```

#### Best-practice example

- Produces a generic high-quality example for the selected question, role level, and interview type.
- Labels it clearly as an illustrative example.
- Never uses first-person claims that could be mistaken for the member's real history without an explicit warning.
- Explains why the structure works.

#### Use my history

- Uses only confirmed history permitted for Interview Studio.
- Displays a compact `Relevant history used` area with source titles or linked Slate records.
- Distinguishes confirmed fact from AI-proposed wording.
- If several examples exist, let the member choose among them rather than silently selecting one.

#### Compare

- Shows the generic structure beside the history-grounded answer or in a clear stacked comparison.
- Highlights structural lessons, not a winner/loser judgment.

### Missing-history behavior

When no sufficiently relevant confirmed history exists:

```text
I do not have a strong example in your Slate for this question yet.
Do you have a situation you would like to add?
```

Actions:

- Talk about it
- Type an example
- Use a best-practice example instead
- Not now

The answer becomes a private candidate Journal/Interview Story draft. AI may ask no more than the focused questions needed to establish situation, role, action, result, and privacy. The member reviews the proposed record before it is saved or connected elsewhere.

### Copy changes

Replace:

- `Evidence-backed coaching` -> `Coaching grounded in your Slate` or simply `Your feedback`
- `Proof you may have missed` -> `Relevant history you may have missed`
- `Model-answer reference` -> remove or replace with the explicit mode control
- `Approved evidence` -> `Approved history` or `Sources from your Slate`

Do not use a score alone as the feedback. The rubric and rationale must remain visible.

## Data requirements

- Shared question repository, question tags, role level, interview type, rubric, and guidance
- Session, answer, original text/transcript, feedback, follow-up, retry, and selected history records
- Retrieval scope saved with each AI run
- Output mode saved as `best_practice`, `member_history`, or `compare`
- Proposed history record remains draft until accepted

## Security and privacy

- Interview sessions and recordings are private by default.
- Public profile AI cannot retrieve private interview material.
- Do not log raw interview answers or transcripts in general application logs.
- The member controls whether an interview story is later connected to Journal, Work, Story, or Resume Creator.

## Required tests

- Mode switch changes grounding behavior
- Generic example never claims member history
- Member-history mode cannot retrieve another member's records
- Missing-history flow creates only a private draft
- Canceling the flow creates no permanent record
- Relevant-history section omits private sources not permitted to Interview Studio
- Original answer remains unchanged after AI improvement
- Follow-up question adapts to at least each major rubric gap
- Voice and text follow the same answer pipeline
- Mobile, keyboard, screen-reader, reduced-motion, empty, error, and retry behavior

## Acceptance scenario

Pete answers a behavioral leadership question. PeerSlate identifies a weak result, asks one useful follow-up, and surfaces a relevant confirmed project from Pete's Slate. In Interview AI, Pete can switch between a generic best-practice example and an answer based on his history. Danielle performing the same flow sees only Danielle's permitted history. When no example exists, the system asks whether the member has one and saves nothing until the member approves a private draft.

---

# 7. PS-BRAND-NAV-001 - Iris Foundry, navigation, and About

## Iris Foundry tokens

Implement shared semantic tokens rather than page-specific hardcoded colors:

```css
:root {
  --ps-canvas: #F7F4EE;
  --ps-surface: #FFFFFF;
  --ps-ink: #191821;
  --ps-muted: /* choose and verify a value meeting contrast */;
  --ps-primary: #5A2D82;
  --ps-bronze: #B87422;
  --ps-success: #16705F;
  --ps-border: /* warm neutral, verified */;
  --ps-page-accent: var(--ps-primary);
  --ps-page-accent-soft: /* derived, verified */;
}
```

Page/room accents:

- Overview/Home: Iris
- Work/Resume: Bronze
- Interview Studio: Teal
- Story: Plum
- Slate Board: Amber
- Community: Pine
- AI: Ultraviolet

Rules:

- Keep most cards neutral.
- Use page accent for orientation, selected states, primary action, and one atmospheric wash.
- Bronze/amber are highlights, not default body text or small white-text fills unless contrast is verified.
- Neutral shadows by default; brand glow only on a hero or open AI surface.
- No global purple wash, colored shadow system, visible grain, or full-card tinting.

## Navigation target

### Logged-out marketing navigation

Recommended:

- How It Works
- Community
- Interview Studio
- Explore a Slate, only if a real visitor experience exists
- Right side: Sign In and Create My Slate

Do not show About PeerSlate as a primary product destination. Place `Why PeerSlate` or `About PeerSlate` in the footer or a restrained marketing-only Company menu.

### Signed-in owner navigation

- Home
- Journal
- Slate
- Work
- Studio
- Community
- Persistent Capture action
- Contextual or global AI action
- Profile/settings menu

### Public member navigation

- Journal
- Story
- Work
- Slate
- Ask [Name] AI

Remove Evidence from public and owner navigation.

## About page rewrite

Retain the route when useful, but change its purpose and label to `Why PeerSlate`.

Required content order:

1. Why PeerSlate exists
2. The problem: meaningful work and life disappear between formal milestones
3. The living Journal and the compounding record
4. Capture -> understand -> choose -> compound
5. How AI helps and what AI never controls
6. Private-first ownership and audience choice
7. What PeerSlate is and is not
8. A working-professional-first call to action

Do not lead with recruiters, fit evaluation, or evidence-backed career marketing. Recruiter value may appear later as a secondary outcome of a member-maintained Slate.

## Required tests

- Navigation by logged-out, owner, connection, other signed-in member, and logged-out public viewer
- No owner-only controls on another member's route
- No About or Evidence item in signed-in/public-member top nav
- All room accents use tokens and meet contrast
- Active states are not communicated by color alone
- 200% zoom, mobile menu, keyboard order, focus management, long labels, and missing avatar behavior

---

# 8. PS-JOURNAL-002 - Journal center, Note, and AI check-in

## Journal product behavior

The Journal is the member's chronological, member-owned record. It contains private drafts and approved entries. Public or connection-visible Journal views are audience-filtered projections of the same records.

Supported entry types include:

- Work update
- Learning
- Win or achievement
- Challenge or work in progress
- Reflection
- Question
- Project movement
- Goal movement
- Milestone
- Personal/life moment
- Photo, video, voice, or document entry

Entry type is helpful metadata, not a required form the member must choose before capturing.

## Journal page requirements

- Private owner timeline
- Search
- Filters: All, Work, Life, Learning, Projects, Goals, Reflections, Questions, Media, Milestones
- Draft, private, selected people, connections, community, and public visibility states
- Edit, archive, delete, unpublish, change audience, and inspect source
- Connected-object chips for Project, Goal, Story candidate, Work/Resume candidate, and Interview Story
- Clear distinction between the original capture and AI-proposed interpretation
- No duplicate record when a Journal entry appears in Community or a Project timeline

## Community right-rail Note

On desktop Community, remove every existing right-side module except one member-owned Note card.

Suggested card title variants:

- A note for later
- Today's note
- Do not forget

Required behavior:

- Plain text editing with autosave and clear saved/saving/error state
- Private to the authenticated member
- Actions:
  - Add to Journal
  - Add to Slate Board
  - Clear
- On Add to Journal, open a review state or Capture with the note prefilled; do not silently create a permanent Journal entry
- On Add to Slate Board, let the member choose an existing column/object or create a private note card
- The card persists across Community modes and returns to the member's latest note

## Rotating AI Journal check-in

Place one quiet line within the Note card, visually subordinate to the member's note. It changes based on time, recent captures, unfinished drafts, and variety—not on engagement optimization.

Example prompt library:

- Anything happen today you may want to remember?
- Did a problem finally move?
- Did you learn something small that may matter later?
- Was there a conversation worth keeping?
- What are you still working through?
- Did you help someone or get useful help?
- Was there a personal win outside work?
- Did a project change direction?
- Is there something you wish you had written down last week?
- Did you make a decision you may need to explain later?

Actions:

- Talk
- Type
- Not now

Rules:

- Default destination is private Journal draft.
- Never publish automatically.
- Never use streak, guilt, scarcity, or red-dot pressure.
- Maximum one proactive prompt presentation per session and a configurable daily limit.
- Dismissal is remembered for the session/day.
- Do not repeat the same prompt until the prompt pool has rotated sufficiently.
- Do not prompt immediately after the member has just captured a meaningful entry.
- If AI proposes a Project, Story, Work, Resume, or Interview connection, show it only after the entry is captured and require approval.

## Required tests

- Note is owner-isolated
- Autosave failure and retry do not lose local text
- Add to Journal creates only a reviewable private draft
- Add to Slate Board does not publish
- Prompt rotation, rate limit, dismiss, recent-capture suppression, and accessibility
- Public and other-member views never receive the private Note content
- Mobile behavior moves the Note to a purposeful drawer or Journal entry point rather than cluttering the Feed

---

# 9. PS-FEED-002 - Community Feed and Respond

## Desktop layout

Use a calm three-column desktop layout only when the viewport supports it:

- Left rail: Community modes, feed filters, and member shortcuts
- Main column: wider composer and Feed
- Right rail: the single Note card from `PS-JOURNAL-002`

Do not add Pick-Me-Ups, challenges, quote cards, people recommendations, interest cards, polls, trends, job/news modules, or promotional content to the right rail.

The Feed mode switch remains persistently reachable so the member can move among the approved Community views without getting trapped.

## Composer

Capture options:

- Type
- Speak
- Photo
- Video
- Document

Do not use `Original transcript`; use `Transcript` or `Captured by voice`.

Remove a separate Preview step. The composer itself is the preview.

Connection options after capture may include:

- Journal, always the canonical record
- My Story candidate
- Slate Board/Goal
- Project
- Work/Resume candidate
- Interview Story

Remove any `PeerSlate proposal` area that makes AI look like the author. AI help may offer narrow actions such as clarify, shorten, preserve my voice, protect confidential details, find the useful detail, or suggest a connection.

## Respond system

Visible action row:

```text
Respond | Comment | Save
```

`Respond` opens a compact intention tray:

- Celebrate
- Support
- I relate
- Ask
- Offer help

Behavior:

- The author may see aggregate counts, but the interface does not rank people or create a popularity leaderboard.
- `Ask` and `Offer help` may invite an optional short note or open a contextual comment/conversation path.
- One member may change or remove a response.
- Repeated clicking must be idempotent.
- Use clear text/icon labels and accessible pressed states.

`Follow progress` is not a universal post action. It may appear on a connected public Project or Goal with an explanation of what will be followed.

## Comments

Implement real behavior:

- Add comment
- Edit/delete own comment
- Reply
- Mention where permitted
- Load more/pagination
- Report
- Author controls for who may comment
- Clear disabled, loading, failure, and retry states

## Prohibited content/surfaces

- No job listings or job cards
- No seeded or AI-generated filler polls
- No About PeerSlate or Ask Pete AI inside Community
- No generic Follow on every post
- No second post table that duplicates Journal content
- No placeholder buttons presented as working

## Acceptance scenario

Danielle captures a private work update, reviews it, publishes it to connections, and connects it to a Project. The same canonical record appears in Danielle's Journal, the Project timeline, and Pete's permitted Feed. Pete selects Support, adds a comment, and saves it. Danielle can edit the source Journal entry and the permitted projections update without creating a second post record.

---

# 10. PS-QUALIFY-001 - Qualification Alignment from uploaded job descriptions

## Purpose

Let a member privately upload an external job description to Ask AI and compare its stated qualifications with the member's confirmed Slate history. This is preparation and self-understanding, not a job board.

## Entry points

- Owner AI attachment control
- Ask [Name] AI attachment control, with strict audience behavior
- Work/Resume Creator `Analyze a job description` action

For a public profile owner or another visitor using Ask [Name] AI, default to public-approved profile sources only. Do not expose private owner history. A signed-in owner may explicitly switch to private Owner AI for a deeper analysis.

## Accepted input

Initially support PDF, DOCX, and TXT. Validate actual file type, size, malware scan state, processing status, and ownership. Provide queued, processing, needs review, complete, failed, canceled, and deleted states.

Job documents are session-private by default. The member may choose to save one privately as a reusable source. Never publish, list, recommend, or index it as a job.

## Extraction schema

Extract and preserve source text for:

```text
job_title
company_name, when present
source_document_id
basic_qualifications[]
preferred_qualifications[]
other_conditions[]
responsibilities[]
location_or_work_mode
travel_requirement
citizenship_requirement
clearance_requirement
education_requirement
experience_years_requirements[]
certification_requirements[]
```

Each extracted qualification needs:

- exact or short source excerpt
- source page/section when available
- normalized requirement
- category
- required/preferred status
- confidence
- member-review state

Do not treat responsibilities as qualifications unless the document explicitly says they are required or preferred.

## Matching schema

For every qualification, produce:

- `confirmed_match`
- `partial_match`
- `not_found`
- `needs_clarification`

Also show:

- member records used
- plain-language rationale
- missing or ambiguous facts
- whether a duration calculation was used
- whether the requirement appears to be a hard gate

Do not use keyword count, embedding similarity, or a skills list as the primary matching method. Those may help retrieve candidate history, but the final classification must reason against the explicit qualification clause and confirmed member facts.

## Scores

Show these separately:

1. **Basic Qualification Coverage**
2. **Preferred Qualification Coverage**
3. **Qualification Compatibility**, optional overall summary

Recommended initial formula, configurable and visible:

```text
Basic score:
  confirmed = 1.0
  partial = 0.5
  not found = 0.0
  needs clarification = excluded from denominator until resolved

Preferred score: same method

Overall Qualification Compatibility:
  75% Basic Qualification Coverage
  25% Preferred Qualification Coverage
```

Important:

- A missing hard-gate basic qualification must be shown prominently even when the overall score is high.
- Never label the result as a probability of interview, offer, selection, or hiring.
- Never claim the employer will interpret the member's history the same way.
- Let the member inspect and correct the mapping.

## Follow-up behavior

When the member record is incomplete, ask focused questions such as:

- The posting asks for five years of systems engineering. I can confirm four from your current Slate. Is there earlier relevant experience you have not added?
- It requires experience leading cross-functional reviews. Did you lead, facilitate, support, or attend the reviews on the X project?
- A clearance is listed as required. Is that information appropriate for you to store here, and should it remain private?

Answers become private candidate records only after review. Do not silently change Work, Resume, Journal, or Career Constellation.

## Result actions

- Review a qualification
- Add missing history
- Correct a match
- Create a tailored Resume draft
- Practice likely interview questions
- Export a private analysis summary
- Delete the uploaded job description

## Required tests

- Required/preferred extraction with source locations
- Responsibilities remain out of qualification score
- Years-of-experience calculation from confirmed dates
- Unknown data creates Needs clarification, not an invented match
- Public Ask AI cannot use private owner records
- Cross-user source isolation and file authorization
- File delete removes access and derived retrieval scope according to retention policy
- No public route, Feed post, index, recommendation, or job listing is created
- Score calculation is deterministic and explained
- Unsupported or malformed documents fail honestly
- Accessibility and mobile review of long requirement lists

---

# 11. PS-RESUME-001 - Resume Creator and PDF vision

## Product vision

The Living Resume web view is the canonical professional presentation. Resume Creator is the owner workflow for creating purpose-specific documents from confirmed Slate records. A PDF is an output snapshot, not the member's primary record.

## Resume Creator location

Inside Work, not a separate top-level application.

Suggested owner route:

```text
/app/work/resumes
/app/work/resumes/new
/app/work/resumes/<resume-id>
```

Use repository conventions discovered during planning.

## Creation flow

1. Choose purpose:
   - General professional resume
   - Target role
   - Internal promotion/review
   - Technical project-focused resume
2. Optional job-description upload or selection from a private saved analysis
3. Choose length/template:
   - Concise one-page
   - Detailed two-page
4. PeerSlate proposes relevant confirmed roles, projects, achievements, promotions, education, credentials, and accomplishments.
5. Member edits inclusion, order, wording, dates, emphasis, and visibility.
6. AI checks for unsupported claims, repetition, vague bullets, missing outcomes, and qualification gaps.
7. Member saves a named version.
8. Export to PDF and DOCX.
9. Optionally designate one approved PDF as the public profile download.

## Content rules

- Projects, achievements, promotions, and outcomes come from canonical Slate records.
- AI may improve clarity but may not invent numbers, ownership, tools, dates, scope, or results.
- Show `Grounded in your Slate` and source relationships in the owner editor, not as clutter in the normal exported resume.
- A member may edit a resume-specific wording variant without rewriting the canonical historical record; preserve the relationship and flag factual divergence for review.
- Keep multiple versions with title, purpose, target, template, created date, modified date, and source snapshot.
- A later change to the Slate does not silently change an already exported version. Show an optional `Updates available` review.

## PDF requirements

- Real text, selectable and accessible—not an image-only PDF
- Standard page sizes and reliable print margins
- Embedded or safe fonts
- Tagged structure when feasible in the chosen generation pipeline
- Links, headings, lists, and reading order tested
- No UI controls, hidden private metadata, internal source IDs, or unpublished information in the export
- Deterministic generation for the same approved version
- Stored privately unless the member designates it public
- Expiring/server-authorized download for private files

## DOCX requirements

- Editable, clean headings and bullets
- No unsupported custom font dependency
- No internal comments or AI annotations unless the member explicitly requests an annotated export

## Required tests

- Multiple resumes per member
- Version isolation across members
- Public default PDF selection and replacement
- Private resume URL authorization
- No invented claims in generated content fixtures/evaluations
- Long names, dense technical content, one-page overflow, two-page pagination, missing dates, and missing education
- PDF text extraction and visual render checks
- DOCX render checks
- Delete/archive/export behavior

---

# 12. PS-CONSTELLATION-001 - Expand Career Constellation

## Product behavior

Career Constellation becomes the visual map of career movement, not a role-only diagram.

Supported node types:

- Role/employer anchor
- Project
- Achievement
- Promotion
- Credential, later or when meaningful

## Relationship rules

- A Project may connect to one or more roles.
- An Achievement may connect to a role, Project, promotion, or outcome.
- A Promotion connects a prior state and a new role/level/date.
- A promotion is never inferred automatically from a title change without member confirmation.
- An item may remain private even when a connected role is public.
- The visual must respect audience filtering before layout is generated.

## Interaction

- Filter by node type, date range, role, and visibility
- Select a node to open a detail drawer with summary, dates, relationships, supporting sources, and approved actions
- Owner actions: edit, connect, hide, publish, add to Resume Creator, promote to Story, or open the Journal history
- Visitor actions only where permitted: inspect, save, or ask public AI
- Avoid decorative empty nodes or AI-invented career relationships

## Accessibility

Provide a synchronized chronological/list view with the same filtered information. Keyboard users must be able to traverse nodes in a logical order. Do not encode node type or state only with color.

## Required tests

- Project spanning roles
- Multiple achievements under one Project
- Promotion confirmation flow
- Private child item under public role
- Audience-filtered graph layout
- No cross-user node leakage
- Keyboard/list equivalence
- Mobile fallback
- Large career history performance

---

# 13. Copy and terminology migration

The implementation plan must inventory and replace user-facing text deliberately. Do not run an unsafe global database replacement.

Recommended changes:

| Current language | Approved direction |
|---|---|
| Evidence | Sources, supporting work, relevant history, or the specific object name |
| Evidence-backed profile | Grounded in approved work / Grounded in your Slate |
| Evidence-backed coaching | Your feedback / Coaching grounded in your Slate |
| Proof you may have missed | Relevant history you may have missed |
| Strongest approved proof | Featured achievement |
| Explore the evidence | Explore the work / See sources used |
| Skill evidence | Skills in practice / Examples from your work |
| Original transcript | Transcript / Captured by voice |
| Model-answer reference | Best-practice example |
| Encourage | Respond, with Celebrate/Support/I relate/Ask/Offer help |
| About PeerSlate in top nav | Remove; use Why PeerSlate in footer/marketing menu |
| Resume page as document | Work + Living Resume + Resume Creator |

Keep `source`, `provenance`, `support`, and audit language where precision is required.

---

# 14. Data and architecture guardrails

The exact schema must follow repository discovery, but the product relationships must be preserved.

## Canonical records

- Journal entry/update
- Project
- Goal
- Milestone
- Achievement
- Promotion
- Role/experience
- Source/document/media asset
- Story moment
- Resume version and resume item selection
- Qualification analysis and requirement match
- Interview session, answer, feedback, follow-up, and story candidate
- Feed projection, comment, response, and save
- Note and Journal prompt event

## Projection rules

- Feed references Journal record ID; it does not copy the post body into an independent truth record unless an immutable publication snapshot is explicitly required for audit.
- Project timeline references the same update.
- Resume item references canonical role/project/achievement/promotion records plus a resume-specific wording variant.
- Career Constellation reads canonical relationship data filtered by audience.
- AI runs record source IDs, retrieval scope, prompt/workflow version, model, output state, latency, and cost where appropriate.

## Deterministic software responsibilities

AI must not control:

- authentication
- authorization
- visibility
- publication
- deletion
- file access
- score arithmetic
- duration calculations
- ownership
- rate limits
- retention
- audit history
- deployment

---

# 15. Staging acceptance journey

The v1.2 implementation program is successful when the following can be demonstrated with separate Pete and Danielle accounts:

1. Pete signs in and sees his private owner Home, Journal, Note, Work, Studio, and Community state.
2. Pete's Community right rail contains only his private Note with a calm Journal check-in.
3. Pete speaks an update, reviews it, saves it privately, then publishes it to Danielle.
4. Danielle sees the same permitted Journal record in Community, selects Support through Respond, and comments.
5. Pete opens Interview Studio, switches between Best-practice example and Use my history, answers a follow-up, and adds missing history only after approving a private draft.
6. Pete uploads a Lockheed-style external job description, receives separate basic/preferred qualification coverage based on explicit qualification clauses, corrects a match, and creates a tailored Resume draft.
7. The uploaded job description never appears as a listing, Feed post, public source, or recommendation.
8. Pete exports a real PDF and DOCX from Resume Creator and chooses one public PDF.
9. Career Constellation displays Pete's roles, Projects, Achievements, and confirmed Promotions; Danielle's private data never appears.
10. A logged-out visitor sees Pete's permitted Journal, Story, Work, Slate, and public Ask Pete AI, but not private sources, notes, analyses, interview sessions, or owner controls.

---

# 16. Start instruction for Claude

Begin with `PS-PLAN-002` only.

Perform the required read-only repository audit. Produce the current-state report, diagrams, risks, dependency map, and prioritized implementation recommendation. Do not modify code, dependencies, data, Azure resources, or configuration until the plan is reviewed and approved.
