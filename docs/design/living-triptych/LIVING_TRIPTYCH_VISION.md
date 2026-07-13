# PeerSlate Overview — The Living Triptych

## North Star

PeerSlate.com is not a traditional portfolio. The Overview page is the cinematic entrance into one connected professional world.

The Living Triptych presents one career through three inseparable dimensions:

1. **My Story — Person**  
   The people, experiences, choices, turning points, and values that shaped the work.
2. **Projects — Builder**  
   The systems, experiments, products, and ideas made real.
3. **Living Résumé — Engineer**  
   The career record, measurable impact, and evidence connected to each claim.

The visitor should understand the page before reading a paragraph. The desired reaction is: **“I have never seen a career presented this way.”**

## Core Composition

The hero is one sculptural installation made from three enormous overlapping translucent slabs—not three ordinary cards.

- **Left slab: My Story**
  - Warm amber and soft gold glass
  - Photography, handwritten notes, maps, life fragments, and human texture
  - Emotional, personal, inviting
- **Center slab: Projects**
  - Deep indigo, azure, and restrained cyan
  - Systems diagrams, product screens, architecture lines, data and interface fragments
  - Precise, inventive, active
- **Right slab: Living Résumé**
  - Cool frosted white and pale blue
  - Career timeline, chapter structure, metrics, evidence cards, and proof links
  - Calm, credible, museum-like

At the overlap, the identity appears:

> Pete Carter  
> Person. Builder. Engineer.  
> Three dimensions of one career.

## Five Canonical States

### 01 — Arrival
All three slabs are legible. Projects may sit slightly forward, but the triptych reads as one balanced composition. The visitor immediately sees Person, Builder, and Engineer.

### 02 — Story Focus
The amber Story slab moves toward the viewer. Photography and handwritten fragments become clearer. Projects and Résumé soften and move backward without disappearing.

Primary message:

> My Story  
> The life that shaped the work.

### 03 — Projects Focus
The indigo Projects slab moves forward. Technical layers wake up: diagrams, interface fragments, product screens, architecture, and impact loops. Story and Résumé recede.

Primary message:

> Projects  
> Ideas engineered into working systems.

### 04 — Résumé Focus
The frosted Résumé slab moves forward. Career chapters, evidence, and measurable impact become clearer. Story and Projects recede.

Primary message:

> Living Résumé  
> The record, connected to the evidence.

### 05 — Entry Transition
The selected slab expands or opens into a luminous threshold and becomes the visual bridge into the destination page. The visitor should feel that they entered another room in the same building rather than loaded an unrelated page.

Possible transition message:

> One career. Three ways in.  
> Choose a dimension. Enter the story.

## Interaction Model

- Pointer hover, keyboard focus, touch selection, and explicit Enter actions must reach the same states.
- The active slab moves forward using depth, scale, lighting, and content reveal—not bounce or spectacle.
- Inactive slabs remain visible so the whole-career relationship is never lost.
- The shared center identity may fade or reposition as one dimension becomes active.
- Selecting Enter initiates the destination transition.
- Navigation remains simple: Overview, My Story, Projects, Résumé.
- Ask the Slate remains a signature utility, visually secondary to the triptych.

## Motion Character

Motion should feel calm, expensive, and intentional.

- Slow enough to understand, fast enough to feel responsive
- Smooth depth shifts and opacity changes
- Restrained parallax and pointer light
- No bouncing, spinning, or constant decorative motion
- Respect `prefers-reduced-motion`
- Transitions should reinforce spatial continuity between Overview and destination pages

## Responsive Interpretation

### Desktop
Use the full overlapping triptych with strong depth and controlled perspective.

### Tablet
Reduce perspective and overlap while retaining the three-slab composition.

### Mobile
Do not shrink the desktop installation. Reinterpret it as a cinematic vertical stack or horizontal carousel with one active slab and neighboring slabs peeking into view.

## Design Language

- Premium light-first theme
- Generous whitespace
- Editorial display typography paired with clean interface typography
- Large glass surfaces with disciplined tinting and edge light
- Soft, layered shadows rather than heavy drop shadows
- One dominant focus at a time
- Real content and evidence wherever possible
- Each destination feels like a different room in the same building

## Non-Negotiable Experience Qualities

- It must not look like three generic SaaS cards.
- It must not become a dashboard full of widgets.
- It must not repeat the full contents of My Story, Projects, or Résumé.
- It must create curiosity and desire to enter each experience.
- Story, Projects, and Résumé must remain visually distinct but structurally related.
- Skills and Evidence are contextual content within Projects and Résumé, not top-level Overview destinations.
- Existing PeerSlate functionality and content should be preserved or deliberately migrated.
- Accessibility, responsiveness, maintainability, and performance are part of the premium experience.

## Engineering Freedom

Codex and Claude Code have equal creative and technical authority. There are no fixed role boundaries. Either agent may inspect, design, prototype, implement, refactor, test, review, or improve any layer of the experience.

Architectural choices should be based on repository reality and working prototypes rather than assumptions. DOM/CSS/SVG, Canvas, WebGL, hybrid rendering, or other approaches may be evaluated. The winning implementation is the one that best balances fidelity, accessibility, responsiveness, performance, and maintainability.

## Recommended Build Sequence

1. Audit the existing repository, Overview page, design system, My Story, Projects, and Résumé implementations.
2. Preserve a known-good baseline and create isolated experimental branches/worktrees.
3. Establish reusable tokens and the slab component model.
4. Build a static desktop Arrival composition using real PeerSlate content.
5. Implement the four interactive focus/transition states.
6. Connect the selected slab to its destination page with spatial continuity.
7. Build tablet and mobile interpretations.
8. Add keyboard, screen-reader, reduced-motion, contrast, and focus behavior.
9. Add visual regression screenshots and performance checks.
10. Roll out behind a feature flag or experimental route before replacing the current Overview.

## Mockup Index

- `mockups/01-arrival.png`
- `mockups/02-story-focus.png`
- `mockups/03-projects-focus.png`
- `mockups/04-resume-focus.png`
- `mockups/05-entry-transition.png`

The mockups establish composition, mood, hierarchy, and interaction intent. They are not pixel-perfect implementation specifications, and generated placeholder imagery or fictional résumé data must be replaced with authentic PeerSlate assets and content.
