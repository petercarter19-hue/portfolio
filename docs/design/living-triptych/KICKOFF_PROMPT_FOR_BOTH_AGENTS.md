# Shared Kickoff Prompt for Codex and Claude Code

You are co-building the PeerSlate Overview redesign with another capable coding agent. You have **full creative and technical authority**. There are no permanent role boundaries: you may inspect, design, prototype, implement, refactor, test, review, or improve any part of the system.

The goal is to implement **The Living Triptych**, a premium, cinematic Overview experience for PeerSlate.com. Read the complete conversation supplied by Pete, then read:

- `docs/design/living-triptych/LIVING_TRIPTYCH_VISION.md`
- every image in `docs/design/living-triptych/mockups/`
- the current repository instructions
- the current Overview, My Story, Projects, and Résumé implementations

Do not assume the stack, routing model, animation library, or component architecture. Discover them from the repository. Preserve existing functionality and real content unless you explicitly document a migration.

## First Mission

Perform a repository and experience audit, then build the first working vertical slice rather than stopping at a written plan.

### Audit

Identify:

1. Framework, rendering model, routing, styling system, state management, animation libraries, build/test commands, deployment assumptions, and browser targets.
2. Every file involved in the current Overview page.
3. Reusable design tokens and components already used by My Story, Projects, and Résumé.
4. Existing content/data sources that should populate each slab.
5. Current accessibility, responsive, performance, and test patterns.
6. Risks created by replacing the current Overview.

Write the findings to an agent-specific audit file under `docs/design/living-triptych/agent-notes/` so the other agent can review them.

### Technical Exploration

Evaluate the best implementation architecture using repository evidence and a working spike. You may consider DOM/CSS/SVG, Canvas, WebGL, or a hybrid. Do not reject an approach solely because it is ambitious; demonstrate its tradeoffs with a prototype.

### First Vertical Slice

Create an isolated experimental route, Storybook story, feature flag, or equivalent lab entry appropriate to the existing architecture. Build the **01 — Arrival** desktop state using authentic PeerSlate content where available:

- three overlapping sculptural slabs
- warm My Story language
- indigo Projects language
- frosted Living Résumé language
- shared identity in the overlap
- basic pointer and keyboard focus selection
- a visible Ask the Slate treatment
- no replacement of the production Overview until the prototype is reviewed

The first slice should establish composition, depth, glass treatment, typography, content hierarchy, and component structure. It does not need final cinematic transitions yet.

## Collaboration Model

Both agents may work on any layer. Use isolated branches or worktrees so experiments do not overwrite each other. Record major decisions in shared design/architecture notes. When approaches differ, preserve both long enough to compare them visually and technically before merging the strongest solution.

Do not optimize for merely completing a checklist. Optimize for the experience described in the vision document.

## Required Output

At the end of the first mission, provide:

1. Repository audit summary.
2. Relevant file map.
3. Proposed component and state architecture.
4. Chosen prototype approach and alternatives considered.
5. Exact files changed.
6. Commands run and test results.
7. Screenshots at representative desktop widths.
8. Known gaps from the approved mockups.
9. Recommended next implementation milestone.

Proceed through audit and implementation. Do not stop after restating the request.
