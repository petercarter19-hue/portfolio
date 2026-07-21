# PS-JOURNAL-001 — Journal, My Story, and Projection Boundary

## The answer to “should Journal and My Story become one?”

They should become one **truth system**, not one **experience**.

- Journal answers: **What have I saved, how has it changed, what is connected,
  who can see it, and what can I do with it?**
- Public/permissioned Journal answers: **What has this person deliberately made
  visible over time to me?**
- My Story answers: **How does this person want me to understand a selected set
  of experiences together?**

Collapsing them would either make Journal too incomplete to manage life or make
My Story feel like an activity log. Keeping separate content stores would
create drift. The correct architecture is shared Moment references with
different projection metadata and interaction models.

## Required distinctions

| Dimension | Owner Journal | Public/permissioned Journal | My Story |
|---|---|---|---|
| Completeness | Complete eligible owner record | Owner-selected, audience-authorized subset | Finite selected narrative |
| Primary order | Chronology plus local filters | Curated chronology/profile timeline | Authored narrative/semantic order |
| Main job | Capture continuity, find, inspect, correct, organize, control, reuse | Let an authorized viewer follow selected visible history | Explain meaning, identity, transitions, and selected chapters |
| Editing | Moment/version/lifecycle/curation controls | Owner edits through owner tools; viewer reads | Story selection, purpose wording, composition, layout, preview, publish |
| Visual form | Functional editorial timeline/list/detail | Polished profile/timeline | Cinematic/spatial authored composition with accessible reflow |
| Data | Canonical Moments + Journal metadata | Authorized Moment/projection fields | Story projection items + separate layout revisions |
| Publication | Individual/curated audience state | Result of explicit owner publication/grant | Separate Story draft and publication |
| AI role | Search, propose tags/connections/next use | Public Ask [Name] only from authorized data | Propose selection/wording/layout; never auto-apply/publish |

## Normative requirements

- **PS-JRN-STY-001:** Journal and My Story shall reference the same canonical
  Moment/version system and shall not maintain independent fact copies.
- **PS-JRN-STY-002:** Journal shall remain complete for the owner even when a
  Moment is removed from Story or every public/permissioned view.
- **PS-JRN-STY-003:** My Story shall not automatically include every Journal
  Moment, imitate recent activity, or use chronology as its only narrative.
- **PS-JRN-STY-004:** Public Journal shall not be implemented as My Story with a
  different label; its timeline/profile purpose and curation controls shall be
  independently comprehensible.
- **PS-JRN-STY-005:** My Story selection, purpose wording, audience, and layout
  are projection state; layout metadata remains separate from content.
- **PS-JRN-STY-006:** Journal curation metadata shall not gain freeform Story
  layout fields or become a parallel Story Composer.
- **PS-JRN-STY-007:** Journal may use the same editorial typography, media
  craft, chapter rhythm, and premium visual quality as My Story while
  preserving functional timeline, search, lifecycle, and semantic order.
- **PS-JRN-STY-008:** Every Story item shall retain an inspectable source/Moment
  relationship for the owner and a public-safe provenance treatment where
  appropriate.
- **PS-JRN-STY-009:** Updating, unpublishing, deleting, or invalidating a Moment
  shall produce explicit Story/projection review behavior without leaving an
  inaccessible layout orphan or silently changing a published claim.
- **PS-JRN-STY-010:** Owner preview shall show the exact public/selected-person/
  Connection/member Story or Journal payload without client-only hiding.
- **PS-JRN-STY-011:** Public navigation labels and cross-links shall explain the
  difference in user testing; if members or viewers cannot predict the result,
  the route/label decision is not ready.
- **PS-JRN-STY-012:** Journal and Story remain usable at mobile width, 200%
  zoom, keyboard, touch, screen reader, and reduced motion. Spatial Story
  presentation retains a stable semantic reading order and structured fallback.

## Recommended product family

The eventual product may expose a family such as:

```text
Journal
├─ Timeline / Manage      complete owner record
├─ Curated Journal        selected timeline and audience preview
└─ My Story               authored presentation from selected references
```

Those labels are illustrative, not a locked route map. The important boundary
is stable even if naming changes.

## Sharing and publication examples

- A member saves a private Moment. It appears in owner Journal only.
- The member later selects it for a Connection-curated Journal. The selected
  Connection can retrieve the exact permitted projection; the Moment remains
  private to everyone else.
- The member writes a Story chapter using the same Moment and chooses a
  purpose-specific sentence. That sentence lives in a versioned Story
  projection and cannot rewrite the Moment.
- Removing the chapter from Story keeps the Moment in Journal and does not
  change a separate public Journal publication unless the member explicitly
  changes that state too.

## Visual acceptance test

Peter's current My Story presentation remains valuable authority for cinematic
quality and authored composition. A Journal design passes only if it reaches
that level of care while still letting a member efficiently find, inspect,
correct, curate, export, archive, delete, and understand visibility. A Story
design passes only if it remains clearly authored rather than becoming a
prettier Journal feed.
