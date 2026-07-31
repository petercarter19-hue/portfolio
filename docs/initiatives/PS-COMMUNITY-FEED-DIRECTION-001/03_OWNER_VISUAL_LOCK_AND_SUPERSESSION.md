# Community Feed owner visual lock and supersession record

## 1. Decision status

- **Owner:** Pete
- **Decision date:** 2026-07-31
- **Decision:** Approve the six-file Community Feed visual set recorded in
  `visual-authority/2026-07-31-pete-lock/MANIFEST.md`
- **Effect:** those files become the production-intent primary-journey visual
  authority for later Community Feed implementation
- **No effect:** no runtime, route, schema, API, shared-governance, messaging,
  merge, deployment, or live-product authority is created

The earlier FD-01 through FD-35 record remains the historical record of the
2026-07-30 direction gate. When a row below names a later visual decision, the
later owner decision controls the Community Feed composition. Unnamed prior
decisions continue unchanged.

## 2. Later owner decisions

| ID | Locked decision | Earlier decision affected |
| --- | --- | --- |
| VA-01 | Lock the six files in the manifest as one coordinated desktop/mobile primary-journey set. No rejected candidate or isolated screen substitutes for the set. | Closes the prior visual-creation gate. |
| VA-02 | Replace the global `In Motion` concept with a post-local `Replies & updates` shelf inside each eligible evolving Feed post. `Threadline Signal` and `Motion card` are internal shorthand only. | Supersedes FD-12's single global section and the corresponding inventory rows. |
| VA-03 | Every eligible shelf is exactly one non-wrapping horizontal row. It may traverse all authorized replies, comments, and author updates. It never wraps, stacks, becomes a grid, or grows a second lane. | Refines FD-13 and supersedes FD-14's three-to-five-total-card limit. |
| VA-04 | A persistent `View all Replies & Updates` action remains outside the scroller and opens the complete traditional vertical conversation. | Replaces `View all In Motion` in FD-14. |
| VA-05 | Selecting a Motion card opens only that selected contribution, with full text/media/actions: centered overlay on desktop and full-screen detail on mobile. Close/back restores exact Feed scroll, shelf offset, and focus. | Adds the selected-contribution state and refines the prior thread-detail inventory. |
| VA-06 | Motion-card attachments use one compact cue only. Multiple attachments reduce to first item plus `+N`; full files, images, galleries, video, and metadata appear after opening. Cards with and without attachments remain equal height. | Replaces the oversized attachment treatment explored during visual creation. |
| VA-07 | Desktop left rail is an owner-specific return rail: `Since you were here`, `Continue the conversation`, `A Spark for you`, and caught-up. It is Community-local and is not declared to be the shared Context Rail. | Supersedes FD-24's ambient Community Pulse left rail. |
| VA-08 | Desktop right rail contains `Community Pulse` and `Active Questions`; personal return context is not duplicated there. | Supersedes FD-25's direct-replies/offers/saved-thread action rail. |
| VA-09 | Spark is a standalone Community contribution prompt. It opens a composer with the prompt attached, but creates, saves, or publishes nothing until the member explicitly chooses. It is not Break-branded. | Adds the accepted Spark composition and replaces Break-as-prompt assumptions. |
| VA-10 | Remove distributed Break cards from the accepted Feed, rails, Catch up sheet, and caught-up ending for the initial implementation direction. Preserve the existing first-class Break destination as a separate, unchanged product surface. | Supersedes FD-23, the Break portion of FD-24/FD-25, FD-29's Break exit, and FD-30's mobile Break placement. FD-19's separate-destination boundary remains. |
| VA-11 | Mobile is a true single-column reflow: no persistent rails; three compact complete Motion cards plus a visible partial fourth at the accepted phone composition; Catch up is a focused sheet containing return context and Spark. | Refines FD-30 and supersedes its mobile Community Pulse and Break-card composition. |
| VA-12 | The Feed ends at an explicit caught-up panel with bounded choices and no automatic refill. | Refines FD-29 to the accepted actions and removes the Break exit. |
| VA-13 | `Message` is visible in the concept as a future communication seam, not an implemented claim. It must be hidden or truthfully unavailable until `PS-MESSAGING-001` or successor authority clears identity, consent, authorization, moderation, and legal gates. | No prior runtime capability existed; this prevents the visual from overstating truth. |
| VA-14 | Journal is not a Community Post launch dependency, and the Feed is not the private Home/profile. Member identity may link to a separately authorized profile destination only. | Confirms FD-01 through FD-03. |

## 3. Resulting Community composition

The accepted Feed is now one coherent model:

- vertical scrolling moves among posts;
- horizontal scrolling moves among the authorized contributions to one post;
- the selected-contribution view provides focus without losing Feed position;
- the traditional full conversation remains one persistent action away;
- the left rail answers `What changed for me and what might I resume?`;
- the right rail answers `What is happening across Community?`;
- Spark gives a low-pressure reason to contribute;
- caught-up gives the session a real ending; and
- The Break remains separate instead of being distributed through this Feed.

This is not a workflow, project stage tracker, timeline, accepted-answer system,
popularity shelf, notification center, second Feed, or private Home page.

## 4. Historical record handling

Do not delete or silently rewrite the original FD record. Its date and owner
approval remain important evidence. Implementers must read this later
supersession record immediately after it. When the old record says `In Motion`,
`From The Break`, left `Community Pulse`, or a right personal action rail, this
record and the Pete-locked visual files control.

## 5. Remaining gates

The visual lock does not clear implementation because:

1. the Community-local rails must preserve their locked, package-local purpose
   and must not be misrepresented as global navigation or popularity furniture;
2. the current visual set does not cover every V1 state; and
3. no dedicated runtime initiative, manager, writer reservation, schema/API
   contract, or release authority exists.

The first-class Community Post truth boundary was subsequently activated by
`PS-COMMUNITY-FEED-AUTHORITY-001`.

Those gates are enumerated in
`05_VISUAL_STATE_GAP_AND_IMPLEMENTATION_GATE.md`.
