# Correction mismatch register — round 3 (Interview Me only)

Owner decisions recorded 2026-08-01 in chat with Pete. This register supersedes
the palette and header instructions in README.md §Locked visual direction and
§Page-local navigation adjudication for this correction round; the 12 locked
PNGs remain composition authority as qualified below.

## Owner decisions controlling this round

1. **Scope: Interview Me only.** Interview AI, Video Practice, History keep
   their released layout untouched. Dark palette applies page-wide (colors
   only) so theme switching is not jarring across tabs.
2. **Light theme keeps the CURRENT released palette.** The green light PNGs
   (01/03/05…) are authority for layout, proportion, and composition only —
   never color. (Pete: "keep the current light theme"; overrides README green.)
3. **Dark theme = smoky-teal/champagne** per dark PNGs (02/04/06…): teal-ink
   stage, overhead lamp glow, champagne accents/primary actions. Sampled from
   locked PNG 02: stage #08181e, cards #0d1e24-ish, champagne button #b29862,
   lamp glow #907354, warm floor #3d3b36.
4. **Real global header stays.** No route-local nav, no suppression of
   .global-header / theme toggle / Search / Sign In. (Overrides README
   "page-local navigation adjudication"; rejected impl b8d1654 built that
   header and is not reused.)
5. **Once the answer exists, released composition rules.** The facelift owns
   only the empty starting state (mic invitation). Drafting-with-text, review,
   and improve keep released structure; styling refinements only.
6. **Left rail accepted with dedupe** (Pete chose "keep rail, dedupe"):
   Different question, Create question, Need a nudge?, Need an example? move
   to a left Practice-tools rail; the right-rail nudge/example cards are
   removed (one home per control). Right rail keeps Session, Up next, Privacy
   (drafting) and Current state / Priority improvement / Browser-local truth
   (review/improve) — released behavior, unchanged.
7. **Sizing is the primary defect being corrected**: rails subordinate
   (smaller type, less padding), center dominant, center type sized to real
   center width; no overlap, clipping, or horizontal overflow at 1536×1024;
   released reflow at tablet/phone preserved (mobile action dock untouched).

## Mockup elements that must NOT be copied (illustrative mistakes)

| PNG element | Why not | What ships instead |
|---|---|---|
| Route-local nav (Home / My Story / Living Résumé / Career Impact, avatar) | Real base.html header is kept (decision 4) | Released global header + released Studio bar |
| Centered "Interview Studio" title + tagline shell, text-only mode tabs | Shell/bar is shared across modes; out of round scope | Released .is__bar with mode tiles, PUBLIC PRACTICE label, demo-profile chip |
| Left rail labels "Get a nudge" / "See an example" | Renaming released controls is forbidden | Released labels "Need a nudge?" / "Need an example?" |
| Duplicate right-rail "Need a nudge?" / "Need an example?" cards alongside left-rail copies | One home per control (decision 6) | Left rail only |
| Missing 5-step progress stepper, question chips, est. time, % complete, "What the interviewer is listening for" | Released informational elements are kept (decision 5) | All retained |
| Missing footer truth strip, "Public demo profile" chip, PUBLIC PRACTICE · BROWSER-LOCAL label | Truth invariants | All retained |
| "SESSION" card fields "Question format / Questions / Role or context" | Released Session card shows Experience / Question family / Format | Released fields |
| Sparse drafting canvas replacing composer metadata | Decision 5 | Mic hero appears only in the empty state, above the released composer |
| Green palette (light PNGs) | Decision 2 | Current released light tokens |

## Functional locks verified before editing

- All hooks are data-attribute-bound; elements move wholesale with attributes.
- JS nudge handler resolves its panel via `closest('.is__context-actions')`
  (interview-studio.js:1228): the left-rail wrapper must carry
  `is__context-actions`.
- Queue dialog + trigger stay in the right rail (`closest('.is__side-column')`
  at js:936).
- Tests pin: mic + review inside `.is__actions.is__composer-actions` (mic
  restyle is CSS-only, no DOM move); exactly one `<aside class="is__side-column"`
  literal (left rail uses `is__tools-rail`); no new `@media (max-width: 24rem)`
  or `(min-width: 64.01rem)` blocks; AI/video panels keep their own
  Different/Create instances untouched.
- Zero JavaScript changes. No route, request, storage, media, score, or
  privacy-copy changes. New static content limited to: left-rail wrapper,
  "Practice tools" group label, and the pictured helper line
  "TYPE OR TALK — Both build the same answer." (locked PNG 01/02 copy).

## Empty-state mechanism (no JS)

Empty = `[data-is-workspace-state="draft"]` root + answer textarea
`:placeholder-shown`. The released Dictate button is enlarged/centered via CSS
in that state only (`display: contents` on the actions row + flex order; no
absolute positioning, no second control, DOM and focus order unchanged). Any
text — typed or dictated — collapses the hero back to the released
composer-first geometry automatically. Scoped to ≥48.01rem so the released
mobile dock behavior is untouched.
