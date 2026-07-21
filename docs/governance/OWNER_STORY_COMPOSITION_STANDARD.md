# PeerSlate Owner Story Composition Standard

_Owner decision: 2026-07-18. Maintained by the ChatGPT Work manager lane._

## Purpose and authority

My Story is a member-curated projection, not an AI-generated collage whose
arrangement the member must accept. The member owns both the approved Story
content and the way that content is composed for an audience. This standard is
the operational architecture and design contract for future authenticated Story
composition work.

This standard is subordinate to the current Bible and Roadmap named in
`CURRENT_BASELINE.yaml`. Every Story design or implementation initiative must
cite it together with `OWNER_VISUAL_INTEGRITY_STANDARD.md`.

## Honest current boundary

The current public Pete My Story page is a polished fixture-driven projection.
Its content and layout are already separated in `static/data/story_data.json`,
but the layout is repository-authored and fixed. A signed-in member cannot yet
drag, resize, layer, save, preview, or publish a personal arrangement.

That current page is useful design evidence, not proof that a multi-user Story
Composer exists. No package may represent this future capability as live before
the authenticated, owner-scoped persistence and publication contracts ship.

## Relationship to the one Journal

Journal and My Story are one truth system with different jobs.

- Journal is the member's complete, chronological, searchable, lifecycle-
  governed record over canonical Moments.
- A public or permissioned Journal is an owner-curated, server-authorized
  timeline/profile projection over selected eligible Moments.
- My Story is a finite, authored, visually composed explanation built from
  selected governed Moment/projection references.

My Story shall not automatically display every Journal Moment or become a
recent-activity timeline. Journal shall not absorb Story's freeform composition
metadata or become a drag-and-drop canvas. Both may share cinematic editorial
quality, typography, media treatment, and chapter rhythm, but Journal must
preserve functional chronology, search, correction, lifecycle, and stable
semantic order while Story preserves purposeful selection and authored
composition.

Removing an item from Story keeps its canonical Moment in the owner's Journal.
Saving a Moment adds no Story item. Public Journal publication and Story
publication are separate explicit actions and may use different eligible
subsets, wording, audience, and presentation state without copying facts.

## Member-owned composition covenant

- The member, not AI, is the final authority over Story selection, emphasis,
  position, size, layering, spacing, media treatment, audience, and publication.
- Direct manipulation shall let the member move and resize supported Story items.
  Where overlap is supported, the member shall be able to control which item is
  in front and keep important image subjects visible.
- Dragging is never the only path. Keyboard controls and a structured inspector
  shall provide equivalent move, resize, layer, and ordering capability.
- AI may offer an optional arrangement proposal, alignment suggestion, or safe
  starting composition. It shall show the proposed change and shall never silently apply, save, overwrite, or publish it.
- Layout editing creates a private draft. Saving a composition and publishing a
  projection are separate explicit actions with exact audience preview.
- The member shall have undo and redo during an editing session, plus a durable
  way to revert to the last saved or published version and restore an approved
  suggested starting layout.

## Required composer interaction

The future Story Composer shall support, where applicable to an item type:

1. select a note, text card, image, media block, or Story grouping;
2. move it by pointer, touch, keyboard, or structured position controls;
3. resize it within readable and responsive minimum/maximum constraints;
4. change foreground/background order without hiding essential controls;
5. adjust an image focal point or crop when the media treatment supports it;
6. use optional snap lines, alignment guides, safe zones, and collision warnings;
7. undo, redo, reset, and restore;
8. preview desktop, tablet, mobile, large-text, and exact audience states;
9. save a private layout draft; and
10. explicitly publish or update a public/permissioned Story projection.

The editor shall never require pixel-perfect fine motor control. All handles and
targets must meet the shared accessibility and touch requirements.

## Responsive and accessible composition

Spatial layout and semantic reading order are separate concerns. Every Story
retains a stable, meaningful reading order for screen readers, keyboard users,
search, export, and narrow mobile flow even when desktop presentation is
spatial. A visual overlap shall never remove content from that semantic order.

The system may store distinct constrained layout profiles for desktop, tablet,
and mobile. A desktop move must not silently create mobile overflow, unreadable
type, hidden controls, or an inaccessible order. The composer shall surface
responsive conflicts before publication and offer a readable automatic mobile
flow that the member can refine.

At 200% zoom or when spatial editing is impractical, the product shall switch to
an accessible structured editor rather than shrinking or clipping the canvas.
Reduced motion shall remove animated rearrangement without removing control.

## Data and architecture contract

- Canonical Capture and Moment content remains single-source. Story items refer
  to exact governed Moment versions or projection records also available
  through the owner's one Journal; layout records
  do not copy authoritative story text.
- Story selection, purpose-specific wording, audience, and layout are governed
  projection data with owner scope, lifecycle, provenance, and revision state.
- Layout metadata is stored separately from content and identifies the Story,
  projection item, breakpoint/profile, position, size, layer, media focal data,
  constraints, version, actor, and timestamps as applicable.
- Draft and published layout revisions are distinct. Publication pins the exact
  content/projection versions and exact layout revision the member previewed.
- Optimistic concurrency or an equivalent conflict contract prevents a stale
  browser from silently overwriting a newer member layout.
- Correction, removal, revocation, deletion, and audience changes propagate
  through Story references without leaving inaccessible or orphaned layout
  records.
- Audit and telemetry record safe action metadata only; they do not copy private
  Story content, image bytes, transcripts, or sensitive layout payloads into
  logs.

## Acceptance example from the owner

On Pete's current Story, the card labeled **The turning point — I went back at 36**
can obscure part of the Maui image, including the sailboat. The future
composer must let Pete select that card, make it smaller within readable limits,
move it so the sailboat remains visible, preview the change at all required
breakpoints and audiences, save it privately, and publish only through a
separate explicit action. The same capability must work for every member; this
example is acceptance evidence, not reusable Pete-specific product logic.

## Future package and entry gate

The reserved implementation package is `PS-STORY-COMPOSER-001`. It is planned, not active,
and does not interrupt PS-VOICE-001 or the current Interview Studio design gate.

Before implementation begins, the package must provide:

- an authenticated owner route and viewer/audience boundary;
- Story projection and layout-revision schema contracts with migration and
  rollback plans;
- complete desktop, touch, keyboard, structured-editor, mobile, 200% zoom,
  long-content, missing-media, collision, stale-version, save-failure, and
  publication-failure designs;
- a named production-intent visual authority and editable source;
- negative tests for cross-user access, stale overwrite, auto-publication,
  canonical-content duplication, and inaccessible drag-only behavior; and
- Pete plus ChatGPT Work design approval before an implementation writer starts.

## Explicitly out of scope for this decision

- No current Story page, fixture, template, CSS, JavaScript, route, or database
  is changed by this governance package.
- The current public My Story page is not converted into an editor.
- AI auto-layout is not authorized as a final or automatically saved state.
- Journal is separately activated under PS-JOURNAL-001; this Story decision
  does not implement or change it.
