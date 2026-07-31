# PeerSlate Community Feed visual authority manifest

## Lock record

- **Initiative:** `PS-COMMUNITY-FEED-DIRECTION-001`
- **Authority state:** Pete-locked primary-journey visual authority
- **Owner approval:** Pete, 2026-07-31
- **Visual creator:** ChatGPT visual-creation lane
- **Visual inspector:** Pete-run iterative inspection and correction
- **Runtime effect:** none; these files do not implement or prove product behavior
- **Authority boundary:** Community Feed only. The private member Home/profile,
  Journal, Studio, Story, Projects, and The Break destination are outside this
  visual lock.

Pete approved the six files below as one coordinated set. Implementation must
compare the rendered product with the matching file and state throughout the
work. A convenient approximation, a prior concept, or one file used as a
substitute for another state is not acceptable.

## Locked files

| File | Locked state | Raster size | Bytes | SHA-256 |
| --- | --- | ---: | ---: | --- |
| `00-desktop-community-feed.jpg` | Desktop Community Feed at rest, including left and right rails, one post-local Replies & updates shelf, varied post media, Spark, and caught-up ending | 696 x 1280 | 155538 | `A35AF42680E4FE5977670A78786210961EB060EAB23F8DA6C0229114DBF39A74` |
| `01-desktop-selected-motion-contribution.jpg` | Desktop selected Replies & updates contribution in a centered focused overlay | 1280 x 853 | 159355 | `E8B550E9C8F23C0502A7B1D427C0ABE6C5F414E1FA74E5C5F89E1D8272A24ACB` |
| `02-desktop-view-all-conversation.jpg` | Desktop complete traditional vertical conversation in a centered overlay | 1280 x 853 | 157463 | `60AD93012195BABD36884970B4E0D979B5E67C9968DA7EA2D2DC7A748524D757` |
| `03-mobile-community-feed.jpg` | Mobile Community Feed at rest with compact one-row Replies & updates shelf | 592 x 1280 | 136993 | `C7B2ECFC55D454EDAC9B275DEAAC28C2DC5622A5884898553D8B9CBA88C71F46` |
| `04-mobile-catch-up-spark-sheet.jpg` | Mobile Catch up sheet containing Since you were here, Continue the conversation, and Spark | 720 x 1280 | 118051 | `60C393F8549177CD6082F7D8C2F6EC39F72A3D93ACBECBC5064F793FC265ACA7` |
| `05-mobile-selected-motion-contribution.jpg` | Mobile full-screen selected Replies & updates contribution | 592 x 1280 | 90154 | `FD580A1DC53B19A1AE05592BFEB84C925C15343E9B3E54F457ED11E2D1EE605D` |

The raster dimensions identify the durable files; they are not CSS viewport
contracts. The implementation package must define exact comparison viewports
that reproduce the accepted desktop and phone compositions without scaling a
raster or shrinking desktop rails into mobile.

## Locked visual and interaction facts

1. Community is a separate Feed destination. It is not the member's private
   Home/profile page.
2. The main Feed is a calm vertical stream with mixed ordinary text, image,
   gallery, and file-bearing posts.
3. An eligible evolving post has one post-local horizontal shelf labeled
   `Replies & updates`. There is one and only one non-wrapping card row.
4. Horizontal movement is manual and available by touch, trackpad, mouse, and
   keyboard. There is no timeline, connector line, progress bar, auto-rotation,
   second row, or stacked lane.
5. The shelf can traverse every authorized contribution. Its persistent
   `View all Replies & Updates` action opens the complete traditional vertical
   conversation.
6. Selecting a card opens only that contribution: a centered overlay on
   desktop and a full-screen detail view on mobile. Closing returns the member
   to the same Feed position, shelf position, and focused card.
7. Motion-card attachment treatment is a compact cue: a small file or media
   icon/thumbnail and a truncated name. Full media and metadata belong in the
   selected contribution or full conversation.
8. Desktop left rail is owner-specific return context: `Since you were here`,
   `Continue the conversation`, `A Spark for you`, then the caught-up state.
9. Desktop right rail contains `Community Pulse` and `Active Questions`.
10. Mobile has no persistent side rails. Left-rail return functions recompose
    into the Catch up sheet. Spark appears there and is not duplicated in the
    normal mobile Feed.
11. Spark is a standalone, optional Community composer prompt. It is not a
    Break card and cannot publish or save without the member's explicit action.
12. No Break card appears in the accepted Feed, rails, Catch up sheet, or
    caught-up ending. The separately governed Break destination remains
    unchanged and outside this visual authority.
13. The caught-up ending is finite and calm; it does not silently refill the
    Feed.
14. `Message` is a future integration seam. It must be hidden or truthfully
    unavailable until the separately governed messaging capability is
    authorized and implemented.

## Exactness and truthful adaptation

The implementation must preserve the accepted hierarchy, density, typography,
spacing, alignments, card proportions, image treatment, borders, color
relationships, rail composition, and overlay behavior. Fixture names, titles,
timestamps, filenames, counts, and photographs illustrate reusable member
content; they are not product logic or proof of live activity.

Only documented, non-material adaptations are permitted without a new visual
lock: truthful live labels, authorized route/shell text, generic fixture data,
WCAG 2.2 AA focus and reflow, localization-safe truncation, reduced-motion
behavior, and permission/error truth. Any adaptation that materially changes
the composition returns to ChatGPT visual creation and Pete for a new lock.

## Completeness boundary

This set locks the primary desktop and mobile journey. It is not the complete
V1 state set required by the Owner Visual Integrity Standard. The missing
states and the gate that prevents premature implementation are recorded in
`05_VISUAL_STATE_GAP_AND_IMPLEMENTATION_GATE.md`.
