# PeerSlate Visual Integrity Standard

_Owner-directed lean revision: 2026-07-31; character and materiality
clarification: 2026-08-01._

## Purpose

PeerSlate should be visually exceptional, accessible, and truthful. This
standard protects an accepted visual direction without making every UI edit a
full design program.

## When it applies

Use the **material visual path** for:

- a new production page or primary journey;
- a new production-intent concept, mockup, or demonstration;
- a material change to composition, hierarchy, dominant object/action,
  typography family, color language, or responsive interaction model; or
- work whose package explicitly requires a new visual lock.

Routine copy, content correction, established-component use, small styling bug,
and non-material accessibility or reflow correction preserve the existing
authority and need only proportionate browser checks. They do not require a
new page inventory, concept round, pass counter, mismatch register, homepage
package, independent visual reviewer, or separate manager audit.

Backend/schema/infrastructure work may close without visual evidence when it
makes no user-facing claim and reports that the experience remains unavailable.

## Authority

- ChatGPT is the sole creator of new or materially revised PeerSlate production-intent visual
  direction. Pete locks the selected durable authority before implementation.
- Existing Pete-locked authorities remain valid until materially revised.
- Codex or Claude may implement a locked authority and make documented
  non-material changes needed for semantic structure, keyboard/focus, contrast,
  touch, reduced motion, truthful state wiring, or text reflow.
- If such a correction would materially change the direction, return that
  decision to ChatGPT and Pete. Do not invent a substitute visual.

An approved mockup is a product promise, not loose inspiration. The production
result must preserve its recognizable purpose, composition, interaction model,
hierarchy, and finish. Truth and accessibility are part of fidelity.

## Character and materiality default

Every new or materially revised production visual gets one **character and
materiality pass** in the workflow. It should feel like an intentional,
contemporary PeerSlate room, not a wireframe or uniform stack of flat rectangles.

Visual prompting and inspection consider:

- foreground, midground, and background relationships;
- restrained neutral shadow on elevated elements;
- subtle surface color, light, gradient, border, or edge shifts;
- texture, imagery, framing, or overlap; and
- type, scale, spacing, and negative space that establish hierarchy.

This is a design default, not an effects quota. Shadows and texture are tools,
not requirements. Quiet or trust-sensitive areas may remain flat when that
improves clarity. Framework-default or visibly unfinished flatness is not an
intentional choice.

Keep the result tasteful:

- use one depth language per room and reuse established tokens;
- elevate the dominant object or true floating layer, not every section;
- keep texture out of text-critical areas; avoid card soup, nested panels, and
  gratuitous glass, glow, grain, gradients, or false-interaction shadows; and
- preserve contrast, focus visibility, zoom/reflow, reduced motion, responsive
  clarity, and performance.

If the result still feels generic or unintentionally flat, refine it in the same
visual round. This adds no separate gate, artifact, pass count, or retrofit
backlog. Existing locks remain valid until revised; the default then informs
the new ChatGPT-created authority Pete locks.

## Lean material-visual workflow

### 1. Define the page

Before visual creation, record a short page brief:

- member and page purpose;
- dominant object and action;
- route/audience and live, stored, private, public, local, fixture, or future
  truth boundary;
- essential content/states and what the page must not become; and
- relationship to the existing room/navigation.

Use `PAGE_PURPOSE_AND_NON_REDUNDANCY_INVENTORY.md` only when the page is crowded,
purpose is disputed, or the owner/package asks for item-by-item disposition.

### 2. Lock direction

ChatGPT creates enough desktop/mobile and critical-state material for the
implementation to be unambiguous. Pete selects the exact authority. Do not
require exhaustive mockups for states that established components already
define and the page does not materially change.

### 3. Implement and compare

The writer implements the locked direction, then compares the real browser at
representative desktop and mobile widths. Check the primary journey plus
loading, empty, failure, long-content, or permission states that can actually
occur and materially affect the page. Correct visible drift before review.

Side-by-side screenshots are the normal proof. Overlay/pixel/geometry evidence
is optional and used when a fixed reference or disputed mismatch makes it
useful. There is no mandatory pass count or separate mismatch ledger; record
only unresolved or intentionally adapted differences.

### 4. Verify quality

Verify relevant keyboard/focus, semantic structure, contrast, touch, 200%
zoom/reflow, reduced motion, long content, and responsive behavior. Test the
states and devices the page actually supports; do not manufacture irrelevant
evidence rows.

### 5. Accept and release

Pete gives the final material visual decision, or explicitly delegates it. A
manager need not duplicate Pete's inspection or the writer's complete-diff
review. The normal PR, pipeline, and affected-route live smoke establish release
truth when deployment is in scope.

## Homepage rule

Check the homepage only when it currently presents or links the changed product
and the change affects that public claim: purpose, name, capability truth,
dominant action, hierarchy, theme, or recognizable interaction. Update the
homepage in the same safe wave or name a bounded follow-up. A routine internal
UI correction does not automatically create a homepage project.

## Completion evidence

For material visual work, record once:

- page purpose and exact locked authority;
- representative desktop/mobile comparison;
- relevant accessibility/responsive result;
- unresolved or permitted narrow adaptation;
- Pete's decision; and
- homepage impact only when applicable.

Keep function, visual acceptance, merge, deployment, and live verification as
separate truthful states.
