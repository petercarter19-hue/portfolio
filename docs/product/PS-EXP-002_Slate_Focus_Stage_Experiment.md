# PS-EXP-002 — Slate Focus Stage: Contextual 3D Workspace Experiment

**Status:** Experiment — approved for a controlled early prototype, not a default product pattern  
**Priority:** Early prototype  
**Decision date:** July 9, 2026  
**Product:** PeerSlate  
**Design system:** Direction C — Newsreader + Inter; product indigo, azure, AI cyan, evidence amber, midnight ink, and cloud white  
**Related feature:** `PS-FEAT-001 — Living Résumé Ledger, Career Constellation, and Voice Builder`

## 1. The Idea Being Preserved

PeerSlate may offer an optional **Focus Stage**: a spatial, glass-based workspace where a member’s résumé chapter, Slate Board, project, or other primary object sits in the center and its meaningful relationships appear around it.

Selecting a related object brings it into a calm foreground inspection state. Dismissing it returns the object to its original place, so the member or visitor can continue exploring without losing context.

This is the interaction language to test—not a promise that every PeerSlate page becomes 3D.

## 2. Product Role

The Focus Stage gives PeerSlate a distinctive way to make relationships understandable:

- a résumé chapter ↔ achievements, evidence, skills, education, projects, and future goals;
- a Slate Board item ↔ related people, work, evidence, milestones, and AI suggestions;
- a project ↔ outcomes, source material, collaborators, and demonstrated capabilities.

The core Ledger and Career Constellation remain the default public résumé journey. Focus Stage is an opt-in contextual explorer and an early test bed for the Slate Board—not a replacement for readable pages, normal navigation, or recruiter-friendly scanning.

## 3. Experience Model

### At rest

- One clear **center canvas** displays the selected résumé chapter or Board item.
- Up to three related objects appear on each side, grouped and labeled by relationship rather than scattered as decoration.
- A subtle depth field and glass layering establish hierarchy while preserving text clarity.
- A visible “Explore related” affordance announces the interaction; nothing relies on hidden gestures.

### Inspecting a related object

1. A user selects a visible related item.
2. It expands toward the foreground into a readable inspection card or panel.
3. The expanded view shows its title, summary, relationship to the center object, source/provenance, visibility state where relevant, and the next appropriate action.
4. A persistent close control, Escape key, and equivalent back action return it to its original side position.
5. The center object remains recognizable throughout; the user never loses their place.

“Throw it out of the way” is translated into a deliberate dismiss-and-return motion. It must feel satisfying, but never depend on physics, a precise drag gesture, or motion that makes the product harder to use.

### Voice entry point

The stage may accept voice requests such as “show the evidence behind this skill” or “connect this Board goal to my current role.” Voice always creates a transcript and a proposed structured action. Changes to facts, relationships, sources, visibility, or publication require explicit review and approval before saving.

## 4. Generic Data Contract

Focus Stage is a renderer of approved relationships; it must not introduce a second, hardcoded content model.

### Required generic concepts

- `SlateEntity`: a member-owned or authorized item, such as an experience, education item, credential, project, achievement, skill, evidence item, Board item, person, or goal.
- `SlateRelation`: a typed connection from one entity to another.
- `FocusStageSession`: temporary interface state only—selected center entity, currently inspected relation, filter, and open/closed state.

### Every relation must retain

- stable source and target IDs;
- owner/profile or equivalent tenant-safe scope;
- relationship type and a member-readable label;
- source/provenance and confidence where AI proposed it;
- audience visibility and authorization state;
- member approval state for AI-created connections;
- ordering or relevance score that can be explained and overridden.

The stage should show only the relations permitted for the current viewer. It never exposes private artifacts merely because they are related to a published item.

## 5. Content and Layout Limits

- One primary center object per stage.
- At most six visible related objects at rest: three on the left and three on the right.
- Additional relationships appear through explicit filters, a “More related” control, or the accessible list view.
- Each visible object has a concise relationship label, not icon-only meaning.
- Skills remain compact. Selecting a skill reveals two or three approved evidence links or proof points; it does not create an unbounded skill bubble cloud.
- Timeline events remain first-class records. A résumé Focus Stage can open from a Ledger chapter or Constellation node while retaining the same timeline context.

## 6. Implementation Boundaries

- Build the early prototype with semantic HTML, CSS transforms, and ordinary DOM layers—not WebGL, a canvas-only interface, or a bespoke 3D engine.
- Use normal route, browser back, deep-link, focus, and screen-reader behavior.
- Make it a feature-flagged, opt-in experiment. Do not alter existing public pages until it passes evaluation.
- Start read-only. Editing and voice actions may open the existing review-and-approval workflow rather than editing inside the spatial canvas.
- Every content item remains independently reachable by URL or standard panel/list view.
- No Pete-specific employers, dates, metrics, or assumptions belong in the component or its fixtures.

## 7. Accessibility and Motion

- Provide an equivalent, fully functional relationship list/drawer for keyboard, touch, screen-reader, high-contrast, narrow-screen, and reduced-motion contexts.
- Move keyboard focus into the inspection view when it opens and return focus to the triggering item when it closes.
- Use clear buttons, names, relationship labels, and close controls; no hover-only or drag-only task.
- `prefers-reduced-motion` opens the ordinary inspection panel with no spatial transition.
- On small screens, default to the standard stacked view; do not squeeze a desktop spatial scene onto a phone.
- Keep transition durations restrained and interruptible. No automatically moving objects or continuously animated background.

## 8. Visual Direction

- Light-first, glass-on-cloud environment with one dominant focus object.
- Direction C color roles only: indigo for product actions, azure and cyan for intelligence/connection, amber for evidence, ink for text.
- No pink, rose, magenta, or coral as semantic interface accents.
- Depth must clarify relationships, not become decoration or obscure usable content.
- Maintain the clean confidence of the Ledger and the cinematic progression of the Constellation while keeping the center object legible at a glance.

## 9. Controlled Prototype Plan

1. Create a read-only Focus Stage using generic fixture data: one résumé chapter and one Slate Board item.
2. Use the existing structured relationship model rather than visual-only mock data.
3. Test a simple path: open stage → inspect evidence → return → inspect a skill → return → exit stage.
4. Test the equivalent keyboard, reduced-motion, and narrow-screen path.
5. Observe whether people understand what is selected, why each item is related, where evidence came from, and how to leave.
6. Only after these results are positive, consider a limited member beta behind a feature flag.

## 10. Evaluation and Exit Criteria

The experiment is successful only if it improves understanding without adding confusion.

| Measure | Prototype success condition |
| --- | --- |
| Orientation | Most participants can identify the center object and the reason a side item is related without instruction. |
| Evidence discovery | Participants can open a skill or achievement and identify its supporting evidence and source. |
| Completion | Keyboard, pointer, touch, and reduced-motion users can inspect and dismiss items without getting stuck. |
| Comfort | No recurring reports of distracting motion, visual overload, or uncertainty about how to exit. |
| Performance | The stage feels immediate on a representative laptop and does not block ordinary page navigation. |
| Product value | It provides clearer relationship understanding than the standard linked-list/drawer alternative for the tested use case. |

If it does not meet these conditions, retain the relationship data and ship the accessible standard view instead. The experiment may be refined or retired without affecting the Ledger, Constellation, voice workflow, or published Slates.

## 11. Future Conversation Resume Point

Resume work with: **`PS-EXP-002 — Slate Focus Stage`**.

The next design task is a single focused prototype for the **Slate Board** using generic data: a central goal or work item, three related objects on each side, one evidence inspection state, and the standard accessible fallback. The next engineering task is a feature-flagged, read-only DOM prototype driven by the generic relation contract above.
