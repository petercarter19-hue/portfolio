# 06 — Test and Acceptance Plan

## Highest-priority visual acceptance

At 1440 × 900, Peter should immediately recognize Photo 1 without explanation:

- the bright physical room and large framed enamel board dominate;
- the left control rail and right board have the same strong size relationship;
- four marker-drawn regions remain spacious, human, and non-gridlike;
- aluminum frame, corners, board depth, tray, markers, eraser, paper notes, pins,
  and restrained shadows read as physical materials;
- the shared PeerSlate header is intact;
- the real section names are Short Term, Projects, Long Term, and Work;
- no later flat-blue or dashboard visual direction is visible.

## Functional acceptance

- Board/List toggle is clear and essential information/actions are equivalent.
- Add/edit/cancel note interactions are keyboard-operable.
- Chalk It Up provides visible listening/typing state and explicit private-draft
  language; no hidden recording or automatic save/publish.
- Proposal review supports edit/remove/cancel/explicit approval and labels any
  fixture or unavailable action.
- Selecting an item opens contextual Focus without replacing the board; close
  returns focus and board state.
- Share, invitation, and publish are visually and conceptually separate.
- Existing routes, header, responsive navigation, Ask AI, browser Back, and
  other pages remain functional.

## Automated and manual matrix

| Layer | Required evidence |
| --- | --- |
| Template/route | 200 responses, shared shell, one page `h1`, four section names, no mockup-only global nav |
| Unit/interaction | view reducer, note state, keyboard movement, proposal mapping, cancel/undo, failure recovery |
| Accessibility | keyboard-only, names/state, focus trap/return, live status, List equivalence, forced colors, reduced motion |
| Responsive | 1440 × 900, laptop, tablet, 390 × 844, 200% zoom, landscape phone, no page overflow |
| Visual | board at rest, listening, proposal review, Focus, List, mobile; compare all Board states to Photo 1's language |
| Regression | Interview Studio and existing navigation tests, full discovered suite where practical |
| Console/network | no uncaught errors, no misleading success, no unauthorized private-data request |

## Review/refine loop

1. Capture desktop screenshot and compare silhouette/proportions first.
2. Correct board dominance, rail width, quadrant spacing, frame, room, and tray.
3. Compare type scale, note placement, marker lines, and small controls.
4. Walk all storyboard states without changing the visual system.
5. Repeat at 390 px and 200% zoom; fix reading order and touch behavior.
6. Record commands, results, screenshots, deviations, and known issues in
   `09-verification.md` before requesting Peter's approval.
