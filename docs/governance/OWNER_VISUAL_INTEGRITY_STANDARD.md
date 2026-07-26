# PeerSlate Owner Visual Integrity Standard

_Owner decision: 2026-07-18; continuous approved-mockup fidelity amendment and
visual-inspection responsibility clarification: 2026-07-26. Maintained by the
currently designated session manager lane._

## Purpose and authority

PeerSlate is expected to be a visually exceptional, professional product. A
correct backend and passing tests are necessary, but they are not enough to call
a user-facing package complete. This standard converts that owner expectation
into a repeatable design, implementation, review, and release gate for every
computer and delivery tool.

This standard is subordinate to the current Bible and Roadmap named in
`CURRENT_BASELINE.yaml`, but it is the controlling operational interpretation
of the Bible's visual-integrity requirements. Every user-facing initiative must
cite it and name its specific visual authority before implementation.

## Non-negotiable product promise

When Pete approves a mockup, storyboard, walkthrough, or demonstration as the
production-intent visual authority, it becomes a product promise. The real
experience must be recognizably the same interaction model and must match or exceed
its hierarchy, composition, clarity, finish, and professional quality.
It may not silently ship as a flatter, more generic, or less polished version.
When the authority is an approved mockup, that exact mockup remains the primary
visual authority throughout implementation, review, correction, acceptance, and
release. It is not first-pass inspiration, and the current implementation never
replaces it as the comparison baseline.

Truth and beauty are simultaneous requirements:

- A demonstration must clearly identify what is illustrative, what is live,
  what is stored, what is transmitted, and what requires sign-in or later work.
- A demonstration may show an approved future experience, but it may not claim
  that the future behavior is already live.
- The eventual product may depart from the approved visual only through a
  narrowly documented truth, accessibility, or responsive-reflow adaptation
  that preserves the locked direction, or through a revised ChatGPT-created,
  Pete-locked authority. A usability or quality change that alters the locked
  composition, hierarchy, dominant object/action, typography family, color
  language, or responsive interaction model is material and requires the
  revised-authority path. No change may be used as cover for visual drift or a
  downgrade.
- No public or member-facing package uses "function now, polish later" as its
  release strategy unless Pete explicitly approves a clearly labeled internal
  preview. An internal preview is not a completed production experience.

## Definitions

- **Visual authority:** the exact named mockup, screen set, storyboard,
  walkthrough, or existing production state that controls the package's look
  and interaction hierarchy.
- **Visual-creation lane:** ChatGPT is the sole creator of new or materially
  revised PeerSlate production-intent concepts, mockups, storyboards,
  responsive/state sets, style exploration, and image assets. Pete locks the
  exact durable output before implementation. Authorities Pete locked before
  the 2026-07-24 decision remain valid until materially revised.
- **Production-intent demonstration:** a clearly labeled, non-live walkthrough
  that shows how an approved real experience is intended to work.
- **Match or exceed:** preserve the recognizable composition, interaction
  model, dominant object, hierarchy, content quality, and polish while making
  only documented improvements. It never permits an alternate aesthetic or
  silent reinterpretation of an approved mockup.
- **Exact visual parity:** at the same state and comparable viewport, the real
  implementation reproduces the authority's visible silhouette, composition,
  placement, proportions, spacing, typography, color, borders, radii, shadows,
  imagery, density, control treatment, and responsive relationships, except for
  a narrowly documented truth, accessibility, or reflow adaptation allowed by
  this standard.
- **Visual mismatch register:** the compact per-pass record of each visible
  difference from the authority, the correction made, and the comparison that
  closed it.
- **Visual inspector:** either Pete when he states that he is personally
  performing the visual inspection, or the assigned writer/agent when Pete is
  not personally performing it. The initiative and completion report record
  which path applies.
- **Visual completion:** manager and owner acceptance of the implemented result
  against the named authority across required states and form factors.
- **Homepage product projection:** a logged-out homepage section, product card,
  or walkthrough that presents or links a real PeerSlate experience. It is a
  distilled public expression of the real product, not a parallel authority.

## Continuous approved-mockup fidelity rule

Whenever an initiative is based on a Pete-approved mockup, including a selected
frame or region within a storyboard or walkthrough, every writer and reviewer
must keep that exact approved mockup open as the continuing visual foundation.
Implementation screenshots, framework defaults, the current build, personal
taste, reviewer preference, or a later polish pass do not supersede or dilute
it.

Before implementation begins, the package records whether Pete is personally
performing the visual inspection. The approved mockup remains the authority
under both paths:

- **Agent-run inspection:** when Pete is not personally performing the visual
  inspection, the assigned writer/agent must execute and document the complete
  compare-refine loop below. This is the mandatory default unless Pete has
  explicitly taken the visual-inspector role.
- **Pete-run inspection:** when Pete states that he is personally performing the
  visual inspection, Pete compares the approved mockup with each real render,
  directs the corrections, decides whether another refinement pass is required,
  and gives or withholds final visual acceptance. The writer implements every
  correction, returns the updated render, and keeps the approved mockup as the
  authority. A second autonomous agent inspection, pass count, or mismatch
  register is not required unless Pete asks for or delegates it.

The following compare-refine loop is mandatory for the agent-run inspection
path:

1. Review the exact approved mockup immediately before the first implementation
   pass. Record its durable path, hash when available, selected frame or region,
   depicted state, and intended viewport.
2. Implement one bounded pass from that authority.
3. Render the real implementation in the corresponding state and comparable
   viewport and capture a named screenshot.
4. Review the approved mockup again. Compare it with the real render
   side-by-side and, when practical, by overlay, pixel sampling, or measured
   geometry. Enter every visible mismatch in the visual mismatch register.
5. Refine the implementation to close the recorded mismatches. Do not edit,
   reinterpret, or replace the approved mockup to make the implementation look
   compliant.
6. Repeat steps 3 through 5, reopening and reviewing the approved mockup during
   every cycle. There is no fixed maximum number of passes. Continue until the
   mismatch register is empty at that state and viewport, except for narrow
   adaptations explicitly permitted and recorded under this standard.
7. Run the same loop for every required state and viewport. Any later code,
   content, asset, or layout change that can alter the visible result reopens
   the loop before handoff, acceptance, merge, or release.

Under the agent-run path, the loop may end in `Pass` only at exact visual
parity. Under the Pete-run path, Pete determines when the mockup comparison and
directed correction cycle has reached exact parity and whether to accept the
result. Under neither path are "close enough," "recognizably similar,"
functional completion, passing tests, a clean diff, a single comparison
screenshot, schedule pressure, or "polish later" valid substitutes for visual
acceptance. If the authority lacks a required state, conflicts with truth or
accessibility, or cannot support a required responsive behavior, the writer
reports `Conditional` or `Fail` and returns the question through the ChatGPT
visual-creation lane and Pete. The writer does not invent an approximation.

Illustrative names, facts, and capability claims in a mockup remain subject to
the package's truth contract and must be replaced with truthful product content.
Semantic structure, focus visibility, WCAG contrast, touch targets, reduced
motion, truthful state wiring, and text reflow remain mandatory. Those needs are
handled through the narrow documented adaptation path or a revised Pete-locked
authority; they are never a general license for visual drift.

## Required gates for user-facing work

### V0 - Authority and truth boundary

Before design or implementation, the initiative records:

1. the exact ChatGPT-created visual authority and Pete's lock, or the exact
   grandfathered Pete-locked authority when no material revision is proposed,
   plus its durable location, hash when available, selected frame or region,
   depicted state, and intended viewport;
2. which behavior is live, illustrative, future, local-only, private, public,
   sent to a service, stored, or not stored;
3. the dominant object and dominant action for every primary state;
4. all approved first-class input alternatives, such as Speak and Type; and
5. the files, routes, data, and capabilities the package may not change; and
6. whether the logged-out homepage presents or links this experience, which
   section is affected, and whether parity work is required.
7. a completed `PAGE_PURPOSE_AND_NON_REDUNDANCY_INVENTORY.md` using the
   controlled template. Before ChatGPT creates or materially revises a visual,
   every meaningful visible page item, card, control, and status in the proposed
   experience must state its member purpose, source/capability truth,
   action/destination, privacy/audience/lifecycle, unique relationship to the
   rest of the page, and one owner decision: **Keep, Change, Combine, Remove,
   or Defer**. Repeated decoration may be grouped; meaningful elements may not.

Codex or Claude may implement the locked authority, capture real-browser
evidence, identify parity, usability, truth, or accessibility defects, and make
documented non-material adaptations for semantic structure, focus visibility,
WCAG contrast, touch targets, reduced motion, truthful state wiring, or text
reflow. Those adaptations follow the manager-approved deviation record and do
not require a new visual-creation pass when they preserve the dominant
object/action, composition, hierarchy, typography family, color language, and
responsive interaction model.

Codex and Claude may not originate or substitute the visual direction. A change
to any preserved visual-direction control above is material: the writer stops
that visual decision and returns the requirement to ChatGPT; Pete must lock the
revised exact authority before implementation continues. Evidence capture and
bounded critique are not separate visual-creation passes.

### V1 - Design readiness

The design set must include the complete primary journey plus loading,
processing, empty, success, failure, permission-denied, unavailable, long-content,
and recovery states that can occur. It must show desktop, touch mobile, 200%
zoom/reflow, visible keyboard focus, reduced motion, and applicable landscape
behavior. Editable source, component inventory, truth labels, and state mapping
are required. A collage or attractive hero alone is not build authority.

Pete approves the page-purpose/non-redundancy inventory before the visual lock.
The visual lock may not introduce a meaningful item, card, control, or status
that is absent from that approved inventory; a newly needed meaningful item
returns through the same inventory decision before it is locked. This gate does
not prohibit visual refinement or grouped repeated decoration. It prevents a
page from accumulating unexamined product claims, duplicated actions, or
unexplained interface furniture.

### V2 - Implementation comparison

When Pete is not personally performing the visual inspection, the writer must
execute the continuous approved-mockup compare-refine loop, keep a compact
pass-by-pass mismatch register, and provide named final comparison screenshots
plus a concise parity matrix comparing the implementation with the visual
authority. Side-by-side comparison is mandatory; overlay, pixel sampling, or
measured-geometry evidence is required when practical for a fixed mockup and
comparable browser viewport.

When Pete is personally performing the visual inspection, V2 instead requires
the named mockup, the renders Pete reviewed, his correction directions, the
writer's corresponding refinements, and Pete's final visual decision. The
writer does not duplicate Pete's inspection with a separate autonomous mismatch
register unless Pete requests it.

The final comparison must cover silhouette and composition, hierarchy, dominant
action, placement and proportions, typography, spacing, color semantics,
borders, radii, shadows, imagery, content density, interaction states, mobile
behavior, focus, zoom, reduced motion, long content, and failure/recovery. Every
visible mismatch is corrected and compared again. An intentional
visual-direction deviation does not pass through a deviation note; it requires a
revised ChatGPT-created, Pete-locked authority. A narrow non-material truth,
accessibility, or reflow adaptation must state the reason, preserve the
authority's visual direction, and receive designated-session-manager approval
under V0.

When a homepage product projection exists, the comparison also pairs the
accepted real-product screens with that homepage section at desktop and mobile.
It records whether product purpose, dominant action, terminology, truth labels,
theme, hierarchy, recognizable visual language, canonical link, and finish are
current. A polished but stale projection fails this gate.

### V3 - Owner and manager acceptance

The designated session manager reviews functional truth and accessibility. When
the agent-run inspection path applies, the manager also reviews the visual
parity evidence. When Pete personally performs the visual inspection, the
manager records Pete's visual decision and does not repeat his inspection.
Material user-facing work does not pass this gate until Pete gives final visual
acceptance and the manager accepts scope/product readiness, or Pete explicitly
delegates final visual acceptance in writing. A technical handoff marked ready
does not itself authorize merge.

Under the owner-approved self-managed delivery model, the assigned writer first
performs and documents the complete visual comparison when the agent-run path
applies, corrects its own issues, and returns a `Pass`, `Conditional`, or `Fail`
self-certification. When Pete performs the inspection, the writer instead
implements Pete's corrections and records Pete's visual decision. The
designated session manager
may rely on coherent comparison evidence and a focused review of the real
product instead of repeating the writer's complete implementation audit. Pete
and the designated session manager still own final product/visual acceptance;
self-certification does not let a writer approve its own visual gate.
For agent-run inspection, `Pass` additionally requires an empty visual mismatch
register across every required state and viewport, except for the explicitly
approved narrow adaptations recorded under this standard. For Pete-run
inspection, `Pass` requires Pete's recorded acceptance of the corrected result
against the approved mockup.

### V4 - Release integrity

The Azure PR, pipeline, and live verification still apply. After acceptance and
deployment, the assigned self-managed writer verifies the canonical production
route at representative desktop and mobile widths and confirms that deployed
assets match the accepted build. The designated session manager records or accepts that evidence
at closeout and may escalate contradictions. The completion report records
functional status and visual status separately.

When a product release materially changes an experience represented on the
homepage, V4 also records one of two valid outcomes: the homepage projection was
accepted and released in the same wave, or an exact downstream parity package
was activated and sequenced immediately after the real product. The real
product may release first when that dependency is necessary, but the package
must report homepage parity as open until the public projection is current.

## Cross-product homepage projection parity

The logged-out homepage is a sequence of product promises. Each section must be
individually exceptional and showcase-quality, unmistakably about its product,
and as professionally finished as the real experience it introduces. It may
simplify a workflow for a visitor, but it may not collapse into generic cards,
a stale screenshot, a less beautiful imitation, or a claim that no longer
matches production.

The following contract applies to every current and future homepage product
section, including Voice Capture, Interview Studio, Ask Pete AI, Living Resume,
My Story, Slate Board, and any later experience added to `/`:

1. The accepted and live real product is upstream authority for function,
   terminology, truth status, theme, hierarchy, and recognizable interaction.
2. Every material product change triggers a homepage-impact assessment. A
   change is material when it alters behavior, capability status, dominant
   action, information architecture, product name, theme, visual authority,
   responsive model, or professional finish.
3. When impact exists, the homepage section is updated in the same release wave
   when file ownership and sequencing are safe. Otherwise the real product
   releases first and an exact downstream homepage-parity package follows; the
   stale projection is tracked honestly until that package is live.
4. A homepage projection has its own production-intent composition and owner/
   manager acceptance. "Parity" does not require copying an application screen;
   it requires a beautiful visitor-facing distillation that is recognizably the
   same product and links to the canonical current route.
5. Homepage work may never add, imply, or demonstrate capability that the real
   product does not provide unless it is explicitly labeled as a future,
   illustrative walkthrough. Once the real capability changes, those labels
   and states must be reviewed too.
6. Product implementation and homepage projection use separate evidence even
   when shipped together: named desktop/mobile comparisons, truth review,
   responsive/accessibility checks, canonical-link verification, and explicit
   Pete/designated-manager acceptance.
7. A homepage redesign may improve the presentation beyond the application
   screen, but it may not become a competing product direction or silently
   redefine the real experience.

## Current owner bindings

### Private Voice Capture

- The accepted homepage Voice walkthrough is the minimum visual and interaction
  authority for the real protected Voice Capture experience. The real UI must
  look recognizably like that demonstration or better.
- Speak and Type are first-class choices in the opening experience. Voice may be
  emphasized, but Type may not be hidden as an error-only fallback.
- The real product remains truthful: voice or text leads to private review and
  explicit **Save private Capture**. It does not automatically create a Moment,
  placement, Journal entry, share, or publication.
- Required review evidence includes microphone permission, recording,
  waveform/timer, stop, upload/transcription, editable transcript, playback,
  retry, private status, explicit save, text path, failures, desktop, mobile,
  keyboard, and 200% zoom.
- Any later material Voice function or visual change triggers review of the
  homepage Voice section under the cross-product parity contract. The released
  protected product becomes the upstream reference for that public story.

### Interview Studio

- The exact source image
  `C:\Users\peter\iCloudDrive\Documents\Career\Website\Changes\Interview Studio\ChatGPT Image Jul 19, 2026, 12_09_58 PM (5).png`
  is the current public Studio visual authority. Image 5 Concept A,
  **Editorial Studio Ledger**, controls default/light; Image 5 Concept C,
  **Cinematic Studio**, controls optional dark. Image 1A and Image 2A are not
  co-authorities.
- The current `/interview-studio` remains one real interactive, light-first
  Approach A public experience. Dark is an optional theme of that same public Studio and route,
  semantic DOM, information architecture, state machine, behavior, and truth
  boundary; it is not an authenticated product or separate feature set.
- Both themes must keep honest public-profile grounding, browser-local history,
  real coaching requests, local camera behavior, and the current primary
  written-practice flow. Changing theme must not reset or alter product state.
- Implementation is not authorized until the complete nine-screen current-public
  design set in both themes, responsive and accessibility states, editable
  source, component inventory, truth review, Claude/Fable feasibility review,
  manager review, and Pete's visual approval are complete.
- Pete later authorized a separately scoped homepage Interview Studio
  walkthrough. That decision supersedes the earlier worked-example exclusion
  only for a future homepage demonstration package; it does not replace the
  interactive public Studio or authorize a homepage edit in the current package.
- The real public Studio is the upstream authority for that walkthrough. The
  walkthrough is a later static, no-side-effect projection of the accepted and
  live Studio, not a parallel design authority. It must use the real Studio's
  5A-light/5C-dark composition, written-practice-first hierarchy, product names,
  and truth labels when final projection parity closes.
- Pete explicitly accepted the completed fixed pre-convergence walkthrough for
  an interim live illustrative release on 2026-07-19. That narrow exception
  allows the truthful, fictional, no-side-effect walkthrough to remain live
  while the real Studio gate proceeds. It does not make the walkthrough a
  co-authority or close homepage parity. Its Voice-default framing and
  paper-light dark modal remain required downstream convergence work after the
  exact 5A/5C real Studio is accepted and live.
- Real Studio implementation and homepage-demo implementation require separate
  visual acceptance, Azure release, and live verification evidence. A demo may
  never be used to claim that the real Studio is implemented or deployed.
- The future authenticated owner Studio remains a separate package after
  authenticated routes, identity, persistence, and authorization exist. The
  current public dark theme does not simulate or pre-authorize it.

### Homepage boundary

The current homepage as a whole is not an approved quality baseline. Every
section must ultimately reach the owner's showcase-quality bar; improving one
section does not certify the rest of the page. The specifically accepted Voice
walkthrough remains the original minimum for Voice Capture, but later accepted
product improvements flow back to the homepage under the cross-product parity
contract. The future Interview walkthrough is governed by the accepted real
Studio and receives its own focused acceptance only after that Studio is
released. A broader homepage redesign remains a separate later initiative and
must preserve these product-specific authority links across the entire page.

### Member-directed My Story composition

- Story polish does not authorize AI or a fixed template to control the
  member's final arrangement. Follow
  `OWNER_STORY_COMPOSITION_STANDARD.md` for the full interaction, accessibility,
  responsive, data, draft, and publication contract.
- The member shall be able to move and resize supported Story items and control
  overlap/layering while preserving accessible semantic order and mobile flow.
- Any AI arrangement is a reviewable proposal. Member-controlled composition,
  exact responsive/audience preview, and explicit publication are part of
  visual acceptance for the future Story Composer.
- The current public Pete Story is fixed fixture evidence, not proof that the
  authenticated multi-user composer is live.

## Backend-only and infrastructure packages

A backend, schema, or infrastructure foundation may merge without a visible UI
only when it makes no user-facing claim and its report states that the member
experience remains unavailable. It may be technically complete for its bounded
scope, but it cannot be represented as a visually complete product experience.

## Required completion-report language

Every material user-facing completion report must state:

- the named visual authority;
- the visual inspector: Pete personally or the assigned writer/agent;
- whether visual parity is Not Started, In Design, In Review, Accepted, or
  Blocked;
- for agent-run inspection, the number of compare-refine passes by state and
  viewport, the compact visual mismatch register, and the evidence that every
  mismatch was rechecked and closed;
- for Pete-run inspection, the renders Pete reviewed, his correction
  directions, the refinements returned to him, and his final visual decision;
- the screenshot and responsive/accessibility evidence reviewed;
- every approved narrow truth, accessibility, or reflow adaptation and why it
  preserves the authority rather than creating a substitute direction;
- the homepage-impact assessment, affected section and canonical link, parity
  status, comparison evidence, and exact downstream package when still open;
- Pete's and the designated session manager's acceptance status; and
- the honest distinction between demonstration, implementation, deployment,
  and live production behavior.
