# Opportunity Slate visual set for Claude

Date: 2026-08-02

Purpose: architecture and implementation-handoff preparation. This set does not itself authorize runtime implementation, repository changes, merge, or deployment.

## Contents

1. `01-PRIMARY-Role-Bring-a-role.png`
2. `02-PRIMARY-Review-Source.png`
3. `03-PRIMARY-Review-Requirements.png`
4. `04-PRIMARY-Alignment-Unsaved-VISUAL-AUTHORITY.png`
5. `05-PRIMARY-Alignment-Saved-STATE-ONLY.png`
6. `06-SUPPORT-Role-Voice-Active.png`
7. `07-SUPPORT-Role-Source-Processing.png`
8. `08-SUPPORT-Requirements-Analysis-Processing.png`
9. `09-SUPPORT-Fallback-Lifecycle-Continuity-States.png`
10. `10-REFERENCE-ONLY-Workshop-Typography-Palette.png`

## Authority hierarchy

- Images 1-5 define the primary flow: Role, Review Source, Review Requirements, Alignment unsaved, and Alignment saved.
- Image 4 is the exact Alignment authority for geometry, separate cards, shadows, visual depth, and the uniform 12-pixel card spacing.
- Image 5 is authority only for saved-state content and actions. Its flatter geometry, compressed card spacing, and blue-heavy palette must not be implemented.
- Images 6-9 define supporting behavior and state truth.
- In Image 8, requirement-correction controls become read-only while analysis runs. Cancel analysis restores editing.
- Image 10 is a typography and palette reference only. It does not place Opportunity Slate inside Workshop and does not authorize Workshop navigation.

## Locked cross-cutting rules

- Opportunity Slate is separate from Workshop.
- Ask Slate AI remains available in the Opportunity Slate subheader.
- Use near-black navy for headings and primary text, muted slate for supporting copy, and cobalt primarily for actions, links, selected outlines, and important icons.
- Green means saved or supported. Amber means partially supported or recoverable warning. Slate gray means not enough information.
- Required and Preferred qualification accounting remains visible without an overall score, percentage, recommendation, employer prediction, or traffic-light verdict.
- Voice and text edit the same member response. Voice never automatically submits, confirms, analyzes, saves, publishes, or navigates.
- AI proposes; the member confirms.
- Nothing saves, publishes, shares, deletes, or reanalyzes without explicit member action.
- Processing remains bounded and local to the workbench.
- Saved state and analytical currency are separate truths.
- Previous saved results remain identifiable and are never silently overwritten.

## Claude's assignment

Read `CLAUDE-ARCHITECTURE-HANDOFF-PROMPT.md` and produce the architecture-ready visual-authority and implementation handoff. Do not generate more images or write runtime code unless Pete separately authorizes that next lane.

