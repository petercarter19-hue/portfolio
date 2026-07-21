# PS-JOURNAL-001 — Experience and Information Architecture

## The unified model

The product does not ask a member to think in database objects. The member sees
one lightweight act—Capture a Moment—and one dependable home—the Journal.
Focused rooms remain useful because a Moment can be used there without being
copied or re-entered.

```text
any eligible signed-in room
        ↓ Capture action (no navigation)
universal composer: Type | Speak | later supported media
        ↓ Save Moment
private source + canonical member-saved Moment
        ↓ derived immediately
owner's one Journal
        ↓ optional now or later
Story | Work | résumé | Project | Board | Studio | Feed | message | public Journal
```

## Universal composer state model

| State | Member sees | Required behavior |
|---|---|---|
| Closed | Persistent Capture action appropriate to the shell | Does not consume a permanent navigation destination |
| Open/empty | Type and Speak as equal choices; private state | Origin context preserved; no destination choice required |
| Composing text | Editable content, privacy, cancel/save | Local recovery behavior is truthful; no hidden save |
| Recording | Time/limit/permission state, stop/cancel | Original remains private; Type remains available |
| Transcribing | Real processing state and safe exit behavior | No fake result; source survives according to policy |
| Review voice | Playback when retained, editable transcript | Transcript correction before canonical acceptance |
| Media processing later | Upload/progress/source state | Save/continue behavior depends on approved media contract |
| Saving | One idempotent Save Moment operation | Duplicate input blocked; focus/status announced |
| Saved | “Moment saved privately,” View in Journal, optional relevant use | Returns to origin; no Add to Journal step |
| Enrichment pending/failed | Moment is safe; optional analysis needs time/retry | Save is not falsely reported as failed |
| Save failed | Exact failure and recovery/draft state | Journal does not show a nonexistent Moment |
| Conflict/stale | What changed and safe reload/merge path | No silent overwrite |

The composer may be a desktop side sheet, contained dialog, mobile bottom/full
sheet, or inline layer when a room requires it. These are responsive
compositions of one state machine, not separate products.

## Origin-context behavior

Origin context helps after the member has described the Moment:

- From Studio: offer to preserve a learning or connect it to the practiced
  answer.
- From résumé creation: offer to use the Moment as a candidate source, never to
  rewrite the résumé automatically.
- From Story: offer to consider it for Story, never to place or publish it.
- From Work/Project/Board: offer a governed relationship or purpose-specific
  draft.
- From Home/Journal: offer one calm next step or simply finish.
- From a public page: require sign-in before private save; do not imply that a
  logged-out browser wrote to a Journal.

Context may preselect a suggestion after save, but not a destination,
visibility, or publication. The member can dismiss every suggestion.

## Owner Journal opening hierarchy

The opening viewport should make one dominant object clear: the member's
longitudinal record. A recommended hierarchy is:

1. identity/mode and privacy orientation;
2. one restrained Capture action;
3. chronological timeline/list with local view controls;
4. optional source-linked return value when eligible;
5. deeper search, filters, curation, relationships, media, and lifecycle below
   or progressively disclosed.

The Journal can inherit the cinematic editorial quality Peter values in My
Story—typography, chronology, media treatment, chapter rhythm, spaciousness,
and meaningful emphasis—without becoming a drag-and-drop canvas or sacrificing
search, lifecycle controls, semantic order, or long-history performance.

## Owner Journal views

- **Timeline:** complete active history in deterministic chronology.
- **Manage/list:** denser search/filter/edit/archive/export workflow.
- **Curated Journal:** an owner-defined subset/emphasis, potentially used to
  preview a public or permissioned timeline.
- **Moment detail:** source, accepted version, revisions, relationships,
  audience/publication, uses, and lifecycle.
- **Archive/deleted-state views:** explicit and separate from the default
  record.

These are local modes, not new top-level products. The exact labels require
production-intent design and user comprehension testing.

## Viewer Journal hierarchy

A non-owner view is intentionally simpler:

1. whose Journal/profile this is;
2. the actual viewer mode or audience context when helpful;
3. owner-selected chronological or curated Moments permitted for that viewer;
4. contextual paths to Story, Work, selected projects, résumé, or Ask [Name]
   AI only when those destinations are also authorized;
5. no owner editing, raw sources, private insights, hidden counts, or disabled
   controls that imply unavailable access.

## Navigation constraints and open work

Locked:

- Journal is core.
- Capture is a global action, not a target destination.
- contextual controls do not become a second global navigation system.

Open until a route-map package is approved:

- exact signed-in top-level labels and order;
- whether desktop and mobile expose identical labels or equivalent composition;
- the canonical authenticated Journal route;
- public Journal/profile route family and slug collision behavior;
- how Slate, Journal, Work, Story, Studio, Community, and More are grouped;
- how the legacy `/app/capture` route transitions;
- whether a central Capture control appears visually in navigation chrome while
  remaining an action rather than a route.

## Accessibility and responsive behavior

- Opening and closing the composer restores focus predictably.
- Status changes use programmatic announcements without repeated interruption.
- Every icon has an accessible name; privacy and processing never depend on
  color alone.
- Timeline chronology remains semantically ordered even when desktop styling is
  spatial or layered.
- Keyboard and structured controls cover every action; pointer drag is not
  required for curation.
- At 200% zoom, the Journal becomes readable document flow without clipped
  controls or horizontal dependence.
- Mobile keeps touch targets, source/privacy clarity, search/filter access, and
  lifecycle controls without shrinking the desktop composition.
- Reduced motion removes decorative timeline transitions while preserving
  location and state cues.
- Long content, long years, many media items, missing media, slow search, empty
  results, and partial downstream failures have intentional designs.

## Visual authority work still required

The approved Journal/My Slate storyboard controls ambition, hierarchy, and
quality, but it predates this corrected universal-composer and one-Journal
contract. Before implementation, a production-intent visual package must show:

- universal composer launched from at least Home, Journal, Story, and Studio;
- text and voice parity;
- saved/failed/enrichment-pending states;
- owner timeline/manage/detail/curation;
- selected-person/Connection/member/public payload differences;
- clear Journal versus My Story paths;
- desktop, 390px mobile, 200% zoom, keyboard focus, reduced motion, empty,
  long-content, restricted, and failure states; and
- exact truth labels for what is live, planned, unavailable, private, public,
  or simulated.
