# PeerSlate Context Rail Standard

**Owner decision:** Peter Carter, 2026-07-21. **Author:** Claude Code (Fable),
designated manager. **Status:** Approved direction; each room's adoption is its
own deliberate, owner-accepted package. This standard authorizes the *pattern*,
not any specific page change.

## 1. What the Context Rail is

One shared "spine" component: a slim rail beside the page's content stage that
holds that room's **local views, sections, chapters, filters, or tools**. The
skeleton (position, geometry, typography, materials, behavior) is identical
everywhere it appears; the **contents and flavor are tailored to each room**.
The owner's analogy: the MacBook Touch Bar — same place, contextual contents.

The accepted JOURNAL-01 contents rail (chapters 01–06 with subtitles, gold
active state, book character) is the **reference implementation** of this
standard.

## 2. The two laws

**Law 1 — the rail never leaves the room.** Every rail entry navigates or
filters *within* the current room/page only: chapters of the Journal, sections
of the résumé, views of the Community board, tools of the Slate Board. A rail
entry may never link to another page or route. The global header does travel;
the rail does depth. This keeps the rail inside the existing governance
boundary for contextual room controls (AGENTS.md Navigation; site rules 22 and
71; `PS-JRN-IA-003/004` pattern) and means the rail is **not** a navigation
change requiring a route-map gate.

**Law 2 — adoption is deliberate, never default.** The owner's words: "It has
to be of purpose. If it just doesn't make sense for one of the pages, then we
don't do it. No tacky. It doesn't flatten it." A page adopts the rail only when
its package answers yes to all four:

1. Does this page have 3–6 genuine internal views/sections/tools members
   actually switch between?
2. Does the rail *replace* an existing weaker control (not add a new layer)?
3. Can the rail speak this room's language without costume (its own label,
   entries, icons, whispers)?
4. Does the page's character survive — or improve? If the rail would flatten
   the room's personality, the answer is no.

## 3. The skeleton (identical wherever adopted)

- Desktop: left rail beside a slightly narrowed content stage; small uppercase
  room label (CONTENTS / SECTIONS / BOARD / …); 3–6 entries, each with icon +
  name + optional one-line subtitle; exactly one gold active state.
- Behavior: scroll-following active state where entries map to scroll sections;
  optional quiet counts (" · 3") and state cues (e.g., a small playing
  indicator). Counts are content counts (items in a section) — never activity
  streaks, recency scores, or engagement metrics; informational only, never
  engagement bait, never streak/points/urgency framing (site rule 24).
- Mobile twin: the same entries as a slim horizontally scrollable chip-row
  under the page title — same icons, same single active state. The chip-row is
  the contextual layer paralleling the desktop rail and is independent of the
  existing global mobile tabbar (`mobile-nav.js`); it does not modify, extend,
  or duplicate that tabbar. No new bottom bars, no third navigation layer.
- Materials: Deep Navy Gold tokens only; Newsreader/Inter; the shared component
  consumes central tokens (one place to style). Consolidating today's
  per-page palette redefinitions is a future aspiration this pattern enables —
  not something any rail package performs implicitly.
- Accessibility: rendered as a labeled `nav` (scoped, e.g. "Journal sections")
  or listbox as appropriate; full keyboard operability; visible focus; correct
  `aria-current`; 200% zoom reflow (rail folds to the chip-row); reduced-motion
  variant for the scroll-following behavior.

## 4. Per-surface disposition (owner-reviewed 2026-07-21)

"Room" vs "page" wording follows the owner: Community is a room; the résumé is
a page; both may carry the rail — what matters is the four-question test.

| Surface | Disposition | Notes |
|---|---|---|
| Journal (`/app/journal`, J1) | **Yes — reference implementation** | Ships with the J1 frontend; chapters per the accepted JOURNAL-01 |
| Public résumé (`/petec/resume`) | **Yes — first migration** | Already has a right-side section rail; restyle to this standard in its own package. Side/position migration is decided in that package with owner acceptance |
| Community / The Slate | **Yes — later package** | Existing left rail cards (sections, saved, circles) consolidate into the rail; room flavor: warm/social |
| Slate Board | **Evaluate in its own package** | AGENTS.md explicitly forbids another permanent navigation layer inside Slate Board; any rail there could only be a restyle of the existing contextual Board Controls, never a new layer or dashboard, and question 4 decides. AGENTS Slate Board rules unchanged |
| Interview Studio | **Evaluate in its own package** | The mode row (Interview Me / AI / Video / History) is a candidate; test question 4 decides |
| My Story | **No** | Authored cinematic scroll; a rail would flatten it (owner call) |
| Homepage `/` | **No** | Cinematic marketing scenes; no internal views |
| `/experience` (retired), `/peerslate`, placeholder pages | **No** | Retired or under-construction surfaces get no investment |
| Owner app (workspace/settings/capture) | **Later, with the Owner Home lane** | Coordinate with PS-HOME-FRONTEND-001 file ownership before touching the shell |
| Public Journal, Projects, future rooms | **Born with it** | New rooms answer the four questions at design time; if yes, they inherit the skeleton free |

## 5. Implementation sequencing (no big-bang)

- **R0 — Journal (in the J1 frontend package).** The rail ships as part of the
  accepted JOURNAL-01 build; its markup/styles are written as a reusable
  partial + component stylesheet from day one.
- **R1 — Extraction.** After J1 acceptance, the Journal rail component is
  extracted into a shared partial + stylesheet as a pure refactor whose output
  is proven identical by test (same rendered DOM/styles). Any palette or token
  consolidation that changes another page's rendered output is a separate
  package with before/after evidence and owner acceptance — never bundled into
  extraction.
- **R2 — Résumé restyle.** Its own package: existing right rail migrates to
  the standard. Owner visual acceptance required (material user-facing change).
- **R3+ — Community, Board, and candidates.** One room per package, each with
  the four-question test recorded and owner acceptance. Rooms may be skipped or
  deferred indefinitely; the standard creates no obligation.

Each package: one writer, Sonnet implements, Opus reviews, Pete accepts
visually. A room's rail is never merged on the standard's authority alone.

## 6. What this standard does not do

- It does not change any route, navigation, or page today.
- It does not authorize touching My Story, the homepage, or any "No" surface.
- It does not permit rail entries that leave the room (Law 1) or any
  gamification framing (site rule 24).
- It does not replace the Visual Integrity Standard: every adopting package
  still needs its named visual authority and owner acceptance.
