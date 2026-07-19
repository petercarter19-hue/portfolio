# PeerSlate Owner Visual Integrity Standard

_Owner decision: 2026-07-18. Maintained by the ChatGPT Work manager lane._

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

Truth and beauty are simultaneous requirements:

- A demonstration must clearly identify what is illustrative, what is live,
  what is stored, what is transmitted, and what requires sign-in or later work.
- A demonstration may show an approved future experience, but it may not claim
  that the future behavior is already live.
- The eventual product may depart from the approved visual only to improve
  truthfulness, accessibility, responsive behavior, usability, or owner-approved
  quality. Those changes must be recorded; they may not be used as cover for a
  visual downgrade.
- No public or member-facing package uses "function now, polish later" as its
  release strategy unless Pete explicitly approves a clearly labeled internal
  preview. An internal preview is not a completed production experience.

## Definitions

- **Visual authority:** the exact named mockup, screen set, storyboard,
  walkthrough, or existing production state that controls the package's look
  and interaction hierarchy.
- **Production-intent demonstration:** a clearly labeled, non-live walkthrough
  that shows how an approved real experience is intended to work.
- **Match or exceed:** preserve the recognizable composition, interaction
  model, dominant object, hierarchy, content quality, and polish while making
  only documented improvements.
- **Visual completion:** manager and owner acceptance of the implemented result
  against the named authority across required states and form factors.

## Required gates for user-facing work

### V0 - Authority and truth boundary

Before design or implementation, the initiative records:

1. the exact visual authority and its durable location;
2. which behavior is live, illustrative, future, local-only, private, public,
   sent to a service, stored, or not stored;
3. the dominant object and dominant action for every primary state;
4. all approved first-class input alternatives, such as Speak and Type; and
5. the files, routes, data, and capabilities the package may not change.

### V1 - Design readiness

The design set must include the complete primary journey plus loading,
processing, empty, success, failure, permission-denied, unavailable, long-content,
and recovery states that can occur. It must show desktop, touch mobile, 200%
zoom/reflow, visible keyboard focus, reduced motion, and applicable landscape
behavior. Editable source, component inventory, truth labels, and state mapping
are required. A collage or attractive hero alone is not build authority.

### V2 - Implementation comparison

The writer must provide named before/after screenshots and a concise parity
matrix comparing the implementation with the visual authority. The comparison
must cover silhouette and composition, hierarchy, dominant action, typography,
spacing, color semantics, content density, interaction states, mobile behavior,
focus, zoom, reduced motion, long content, and failure/recovery. Any intentional
deviation requires a written reason and manager approval.

### V3 - Owner and manager acceptance

ChatGPT Work reviews functional truth, accessibility, and visual parity. Pete
reviews the real implemented result for professional finish. Material
user-facing work does not pass this gate until both accept it or Pete explicitly
delegates final visual acceptance in writing. A technical handoff marked ready
does not itself authorize merge.

### V4 - Release integrity

The Azure PR, pipeline, and live verification still apply. After deployment,
the manager verifies the canonical production route at representative desktop
and mobile widths and confirms that deployed assets match the accepted build.
The completion report records functional status and visual status separately.

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

### Interview Studio

- Direction A, **Editorial Studio Ledger**, is the selected visual direction for
  the current public Interview Studio design work.
- The current `/interview-studio` remains the real interactive, light-first
  Approach A public experience. It must keep honest public-profile grounding,
  browser-local history, real coaching requests, and local camera behavior.
- Implementation is not authorized until the complete nine-screen current-public
  design set, responsive and accessibility states, editable source, component
  inventory, truth review, Claude/Fable feasibility review, manager review, and
  Pete's visual approval are complete.
- Pete later authorized a separately scoped homepage Interview Studio
  walkthrough. That decision supersedes the earlier worked-example exclusion
  only for a future homepage demonstration package; it does not replace the
  interactive public Studio or authorize a homepage edit in the current package.
- The future authenticated owner Studio remains a separate, dark-first package
  after authenticated routes, identity, persistence, and authorization exist.

### Homepage boundary

The current homepage as a whole is not an approved quality baseline. The
specifically accepted Voice walkthrough is a binding minimum for Voice Capture,
and the future Interview walkthrough will receive its own authority. A broader
homepage redesign remains a separate later initiative and must meet this same
standard across the entire page.

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
- whether visual parity is Not Started, In Design, In Review, Accepted, or
  Blocked;
- the screenshot and responsive/accessibility evidence reviewed;
- every approved deviation and why it improves the product;
- Pete's and ChatGPT Work's acceptance status; and
- the honest distinction between demonstration, implementation, deployment,
  and live production behavior.
