# PS-SLATE-STUDIO-IA-001 — Owner Direction Record (Project Croatia)

**Recorded:** 2026-07-22, from Pete's direction in session with Claude Code
(program manager). **Owner refinements recorded:** 2026-07-23 by Codex at
Pete's direction in Sections 6b–6d and 7. **Status:** owner direction governing
this package's architecture work. Bible/Roadmap amendments derived from this
record are PROPOSED separately and require owner activation per
`DOCUMENT_CONTROL.md`. **Nothing in this record authorizes runtime product
implementation.**

## 1. Product direction

- **PeerSlate is work-first.** It is first a professional identity, portfolio,
  growth, and future-building platform. A professional-casual social layer
  remains downstream ("it can become one, but through the right track").
- **Slate Studio** (working umbrella name) is the signed-in experiential
  center: the member's private career sandbox and Future Builder.
  Positioning, in Pete's words: **"Not a résumé builder. A future builder."**
- **Member-flow order:** *The Studio shapes. Your Slate presents. Community
  connects. Underneath everything, the Journal remembers.* The technical data
  flow (Capture → Save Moment → canonical truth → placement → projection) is
  unchanged. The Journal is architecturally central and experientially
  supporting: *"Journal preserves. Studio activates."* The Journal work was
  not wasted; its lobby position changes.
- **The tagline becomes the experience.** *Your Work. Your Story. Your
  Future.* is the live product statement (site footer, homepage title, Design
  Bible). The Studio is where the three intersect; the Work–Story–Future lens
  on any professional object is to be investigated as a signature interaction
  (interaction model decided by the IA package, not assumed to be three
  columns or pages).
- **The no-intention rule.** The room must reward a five-minute visit with
  zero agenda. *"Start with an idea — or come find one."* Every experience is
  an invitation, never an assignment.
- **Direct editing and AI are equal paths** (reaffirms the doc 14 ruling:
  in-place editing where the member stands is the core requirement; intent
  surfaces are optional hallways, deep links stay primary).
- **Two AIs, one unmistakable boundary.** Ask Slate is the private owner
  collaborator; Ask [Name] AI is the public visitor assistant. Never one
  ambiguous chat surface; anything becoming public knowledge requires
  explicit, previewed approval.
- **The sandbox promise (verbatim, binding):** *"Nothing you try here changes
  what is live until you decide."*
- **The public Slate stays calm.** The Studio absorbs complexity privately;
  Community consumes deliberate projections and never becomes an authoring
  path.

## 2. Owner rulings, 2026-07-22

1. **Spark reschedule — approved.** Universal (no-history) sparks may precede
   the Journal-history-grounded sparks; grounded sparks follow once
   sufficient member history exists. This supersedes, for the universal
   subset only, the PS-RETURN-VALUE-001 "only after the private Journal
   core" staging — formal amendment staged in this package.
2. **Shell — one ruling.** The PS-SHELL-001 / Studio-shell relationship is
   decided in this package (merge, sequence, or retire). Owner-side mockup
   rounds started 2026-07-22 with the delivered instruction pack.
3. **Sequencing — Studio-first, officially.** "This takes priority over
   Journal — reschedule. We are work-professional-portfolio focused. No more
   scope slip." Interpreted with repository evidence (§4): the implemented
   Journal J1 / Community / Owner Home milestone is **finished and landed**,
   not expanded; the Journal-as-destination stops growing after J1; the
   Studio becomes the experiential center that consumes it. The
   `CURRENT_BASELINE.yaml` `next_gate` (staff the PS-JOURNAL-001 private
   core) is superseded — rewrite staged in this package, applied via
   governance.
4. **Wave 1 — integrate and tailor what exists, add the rest.** Reuse-first;
   live foundations carry the load.
5. **Package dispositions — delegated** to Claude Code as program manager
   (deliverable D4/D1 disposition table).
6. **Owner Home — delegated.** "Do what is best for the path for our
   vision." Leading path after verification: land the finite flag-off
   `owner-home.v1` frontend as built; its evolution into or beside the
   Workshop opening surface is decided by the IA package with priced options.

## 3. Delivery workflow (owner-set, 2026-07-22)

| Stage | Role | Assignee |
|---|---|---|
| 1 | Architect + package manager | **Fable (xhigh)** |
| 2 | Sole implementation writer | **Sonnet 5 (xhigh)** |
| 3 | Visual reviewer | **Pete** (with the designated manager, per `OWNER_VISUAL_INTEGRITY_STANDARD.md`) |
| 4 | Independent reviewer | **Opus (xhigh)** |
| 5 | Final audit, governance, closeout | **Claude Code** (this session) |

- **Scope:** the PS-COMMUNITY-JOURNAL-HOME-MILESTONE-001 finish (13-step
  sequence per the 2026-07-22 handoff) and **all Workshop implementation
  waves**.
- **Execution:** orchestrated from the Claude Code session — roles run as
  managed agents under one lane; one-branch-one-writer discipline preserved;
  Pete interacts at the visual-review gate and final acceptance.
- Croatia direction/governance documentation (this package's D1–D7) remains
  with Claude Code as program manager; Claude Code does not audit its own
  authored implementation — under this pipeline the writer is Sonnet, so the
  audit seat is independent.
- **Audit ownership (owner rulings, 2026-07-22, later same day):** Claude
  Code holds complete audit authority; no external ultra runs are required or
  planned (the prior session's Ultra chain ended on usage limits with the
  work substantially complete). **For the milestone specifically, the owner
  also waived the Opus review stage** — the milestone has already been
  through prior review/correction cycles, so its chain is: writer finish →
  Pete visual gate → Claude Code final audit approval. The five-stage
  pipeline in the table above remains the default for future Workshop
  implementation waves.

## 4. Current-state facts this record relies on (verified 2026-07-22)

- `origin/main` = `e1272220f539f41810698855341b9399b14ebd73`. Working
  governance pointer records lag PRs ~126–160 (a mini truth-reconciliation is
  in D1 scope).
- **On main:** backend + flag infrastructure for all three products — Journal
  API/service, `owner-home.v1` data contract, Community routes/base — with
  `PEERSLATE_JOURNAL_ENABLED` and `PEERSLATE_OWNER_HOME_ENABLED` both
  defaulting **false**. No Journal frontend, no `owner_home.html`, no
  Community-tabs package on main.
- **On branches:** implemented frontends — Journal J1
  (`work/2026-07-21-journal-frontend-j1-impl`, tip `099e8e1…`), Community
  tabs (`…community-tabs-impl`, tip `a8c0496…`), Owner Home
  (`…home-frontend-001-impl`, tip `f8c8826…`) — unified with integration glue
  on `work/2026-07-22-community-journal-home-milestone-integration`,
  checkpoint `b02d4a12dccb56a6f8785266f8e32b761e908082` (331 files,
  ~+19.6k lines vs main).
- **Handoff received 2026-07-22:** the prior milestone writer relinquished at
  exactly that checkpoint; frozen source SHAs verified as ancestors; owner
  decision recorded to **defer Journal voice playback** (honest `Coming
  later`; no fake playback). Hard boundaries: both flags stay false; no SQL;
  no migration edits; no shared-governance edits; no PR/merge/deploy until
  the review/audit gates pass; release (flags false) can make Community
  Feed/The Break live and nothing else.

## 5. Sequencing (recommended; finalized in D5)

1. **Land the milestone** via the §3 pipeline → review/audit gates →
   Pete-authorized Azure PR/squash/pipeline release with both flags false.
2. **Croatia direction phase:** D1 assessment + mini-reconciliation,
   dispositions, baseline `next_gate` rewrite, Bible v2.9 / Roadmap v2.8
   amendment proposals, IA package (D3), inventory (D4), wave-1 definition
   (D6), prototype brief (D7) against Pete's accepted mockups.
3. **Workshop wave 1** through the pipeline, per the accepted IA and priced
   cast.

## 6. Dispositions summary

Moves forward: composer + Save Moment machinery; canonical Moment/Placement
foundations; finishing and landing the built milestone; Workshop IA and
mockup rounds; universal sparks (staged); one combined **Build Your Future**
workspace with Slate Board as its central canvas; and the Work–Story–Future
lens as an interaction inside that workspace. Slides back: Journal as flow
center; Journal-destination expansion beyond the J1 finish; grounded personal
sparks (until history + IA); multi-version lenses; a broad public-navigation
overhaul; and immediate physical relocation or renaming of the current live
Interview Studio. Undecided: final umbrella name; Owner Home evolution model;
exact wave-1 cast; the final name and transition model for the broader
practice/coaching system; and the exact responsive interaction for the
Work–Story–Future lens. **Not authorized by this record:** runtime product
code, route changes, flag activations, public-page rewrites, Bible/Roadmap
edits (proposed separately), second truth stores, mandatory-AI flows,
public-by-default anything.

## 6a. Owner design refinement — the command deck (2026-07-22, late)

The Workshop opening surface is a **command deck, not a chooser**. Pete's
framing: "The workshop should be a command center. Think Star Trek, Star Ship
Command, the cockpit." Design consequences, binding on D3 and D7:

- **The opening surface resumes; it does not ask.** The member arrives
  mid-flight: the live Slate is the viewscreen (largest element), the bench
  already holds their most-alive draft, and every station is already on — the
  spark face-up with today's question, materials fanned, the whole deck a hot
  drop target. Entry actions are stations, never doors or menus.
- **Enterprise bridge, not 747 cockpit.** The calm rules survive intact: a
  handful of quiet stations, state lights (draft/live/capture-ready) instead
  of metrics, nothing shouting. "Command center" licenses presence and
  immediacy — never gauges-about-you, counts, or charts.
- This framing strengthens Owner Home **Model A** (Owner Home evolving into
  the deck: its review items become station/state lights) and effectively
  decides the persistent-shell question in Section 13's favor — the room
  persists, the center swaps. D3 prices and confirms both.
- Illustrated in Claude's concept-sketch artifact (plate 01 "command deck"
  revision, 2026-07-22); the sketch remains illustrative, not visual
  authority.

## 6b. Owner IA refinement — Build Your Future and Slate Board (2026-07-23)

Pete approved the Workshop visual system and command-deck direction subject to
the information architecture below. These are direction decisions for D3/D7,
not runtime or route authorization.

- **Target signed-in Slate Studio navigation:** `Workshop | Build Your Future |
  Interview Studio`, with `Interview Studio` retained as a provisional current
  product label until the separately governed naming and expansion decision in
  Section 6c. The signed-in global context is `My Slate | Slate Studio |
  Community`; the member-facing Slate label may be personalized (for example,
  `Pete's Slate`) but is never Pete-specific product logic.
- **Build and Future are one destination.** `Build Your Future` combines direct
  development of the member's existing Résumé, Work, My Story, and Projects
  with grounded exploration of directions, skills, goals, and experiments.
  Build and Future may remain internal modes or lenses, but they are not peer
  navigation destinations.
- **Slate Board is the central canvas inside Build Your Future.** It is not a
  separate Slate Studio tab and is not reduced to a link card. Its spatial,
  tactile character and its Work / Projects / Short Term / Long Term
  relationships are preserved. It must not become a Kanban board, task manager,
  employability dashboard, progress score, or AI prediction surface.
- **The public Résumé and My Story are non-negotiable existing products.** Build
  Your Future develops the governed records and private drafts that feed those
  experiences; it does not create replacement pages or a second dataset.
  Existing public routes and behavior remain unchanged by this package.
- **Creative modes remain inside the room.** The Work–Story–Future lens,
  backstory/evidence drawer, remix/use-another-way flow, draft-versus-published
  comparison, Try Another Future, Career Experiments, Future Postcard/Time
  Capsule, Fitting Room/Qualification Alignment, Skills to Develop, Compass,
  and Receipts/review-day kit remain part of the design vocabulary and staged
  product inventory. They are optional modes, cards, drawers, or later
  experiences—not new routes or a wall of competing features.
- **First-screen restraint remains binding.** A Build Your Future mockup should
  show a small representative set of creative invitations plus an
  `Explore other directions` path. It must not display every preserved idea at
  once.
- **Live Slate preview remains optional/deferred.** The near-term design uses
  clear `Working draft — private` and `View published Slate` status/actions;
  no embedded live preview is required for the first implementation wave.
- **Later visual alignment, not present redesign.** After the Slate Studio IA
  and visual system are locked, separate packages may review the existing
  Living Résumé, My Story, and current Interview Studio for shared-shell,
  typography, spacing, color, card-treatment, and light/dark alignment.
  Those reviews must preserve each product's route, content, behavior,
  interaction model, truth boundary, and controlling visual authority unless
  Pete separately approves a functional change.

## 6c. Owner product refinement — broader practice and coaching Studio (2026-07-23)

Pete ruled that the future job is larger than interviews. The current
`Interview Studio` name and public product remain real and unchanged today, but
the target product direction is one broader AI-guided practice, rehearsal,
review, and coaching system. Interviewing becomes one scenario family rather
than the definition of the whole product.

The unified system must investigate these scenario families together rather
than create a collection of separate Studios:

- job and career interviews;
- presentations, pitches, explanations, and audience-specific rehearsal;
- coaching, review, performance, and promotion conversations;
- difficult professional conversations, including delivering hard feedback,
  telling someone they did not receive a promotion, and preparing to let an
  employee go; and
- other high-stakes professional conversations where private, repeatable
  preparation can be genuinely useful.

The **feedback loop is a core capability**, not decorative AI commentary:
establish the scenario, audience, role, stakes, and constraint; let the member
practice by an available input method; return specific, constructive,
source-grounded feedback; allow a retry or comparison of takes; and let the
member explicitly keep or discard anything useful. The system must not grade a
person, predict employment outcomes, diagnose them, make an HR decision, or
replace legal, policy, or human judgment in sensitive workplace situations.
Where the member authorizes it, practice may be grounded in their real Slate
material; otherwise useful ungrounded practice remains available.

The final umbrella name is deliberately open. `Coaching Studio`, `Practice
Studio`, `Communication Studio`, `Review Studio`, `Presentation Studio`, and
other candidates are inputs to a naming decision, not approved parallel
products. The goal is one understandable place, not a row of Studios.

**Proposed controlled-document placement after the current IA locks:**

1. Add the broader practice/coaching system to the Bible's Slate Studio product
   definition and invariants, with Interview as one scenario family and the
   feedback, privacy, human-authority, and no-scoring boundaries above.
2. Add a Roadmap discovery/naming/architecture gate immediately after Slate
   Studio IA acceptance and before any rename, route transition, visual
   alignment, signed-in grounding, or new scenario implementation.
3. Preserve the current public Interview Studio name, route, behavior,
   browser-local truth boundary, and homepage parity until that separate
   package is designed, accepted, released, and verified.

## 6d. Revisit candidate — ambient Community pulse (2026-07-23)

Pete proposed a later desktop/tablet experiment: a narrow optional live
Community pulse at the left or right edge of the browser workspace so connected
members can feel light ambient activity while they work.

This is **not part of the current Workshop or Build Your Future mockups, D6
wave 1, or present navigation**. Preserve it for later investigation with these
initial boundaries:

- connection-authorized content only, with authorization resolved before
  retrieval;
- a few calm items rather than an infinite feed;
- collapsible and secondary to the dominant Studio workspace;
- no popularity counts, engagement pressure, autoplay, or constant motion;
- desktop/tablet exploration first and hidden on small mobile screens; and
- a doorway to Community, never a second Community authoring surface or a
  source of fabricated activity.

## 6e. Owner visual lock — Build Your Future (2026-07-23)

Pete explicitly locked the corrected Build Your Future dark and light desktop
pair on 2026-07-23. The exact repository files, dimensions, hashes, visual
review, storyboard, functional mapping, and slice roadmap are controlled by
`04_BUILD_YOUR_FUTURE_VISUAL_REVIEW_AND_INCREMENTAL_STORYBOARD.md`.

The visual lock resolves the desktop concept and D7 direction only. It does not
activate product code or satisfy the remaining responsive, accessibility,
state, route, data, package, manager/writer, Bible/Roadmap, or release gates.
The faint Board relationship curves in the locked images represent a
selected-item state; they are not permanent Board decoration. No later mockup
or implementation may restore the rejected crosshair/always-visible arrow
network or flatten the accepted Board + selected-work + creative-directions
hierarchy without a recorded owner-approved deviation.

## 7. Naming rulings

- "Studio Start" — **rejected** (Pete).
- "Open Studio" — superseded 2026-07-22: the opening surface is named
  **Workshop**.
- "Slate Studio" — umbrella **working** name; not locked for navigation.
- **Build Your Future** — owner-selected name for the combined private Build +
  Future workspace containing Slate Board.
- **Interview Studio keeps its current public name provisionally** until the
  separately governed broader practice/coaching definition, naming, and
  transition wave in Section 6c. Its current route and homepage parity contract
  remain closed and binding until then.
