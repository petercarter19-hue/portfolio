# ChatGPT visual-correction handoff — Workshop round 2

**From:** Claude (architecture lane), 2026-08-01
**To:** ChatGPT visual-creation lane
**Initiative:** PS-SLATE-STUDIO-IA-001
**Prior round:** `visual-authority/workshop-candidate-2026-07-31/` (five screens
plus one reference, hash-pinned, `CANDIDATE — NOT OWNER-LOCKED`)

## Authority boundary

ChatGPT is the sole creation lane for new or materially revised PeerSlate
production-intent visual authority. Claude may not originate composition,
hierarchy, dominant object, typography family, colour language, or responsive
interaction model, and has not attempted to here. Everything below states **what
must be true**, not what it should look like — the visual answers are yours.

Pete locks the corrected exact files and hashes. Until he does, nothing is
implementable.

---

## 1. What must not change

The prior round got the hard part right. Protect these:

- **Original wording vs interpretation, shown separately** (screen 03). This is
  the product's core promise made visible. It is the strongest thing in the set.
- **The review rhythm with no grading** — strong points, one standout piece of
  evidence, one thing worth strengthening, one useful question. No score, no
  completeness meter, no deficit language. The star reads as "useful evidence,"
  not a reward; keep it to exactly one per review.
- **The suggestion card** on screen 05 — `SUGGESTED BY PEERSLATE — NOT
  CONFIRMED`, citing real member evidence, with Review / Edit and confirm /
  Dismiss / Do not suggest this again. This should become the template for every
  AI proposal in the product.
- **The downstream-truth banner** — "Changing it here will not silently change
  that draft."
- **Negative-space save confirmation** — telling the member what did *not*
  happen.
- **`Use as context`** and its session-scoped explanation.
- The calm three-rail composition, and the complete absence of gamification,
  streaks, or identity homework.

---

## 2. Required new screen — the blocker

**A final-review and `Save privately` state does not exist in the set, and
nothing can be implemented without it.**

The written direction says the member "reviews the final proposed private
information and explicitly selects `Save privately`." No screen shows that
moment. Screen 03's actions (Edit myself / Save unfinished / Stop for now /
Improve with AI / Add the missing result) reach no save, so the sequence has no
continuity and its most important consent step is undrawn.

It also carries a decision Pete made on 2026-08-01: **accepted AI refinements
are not labelled as AI-changed**, because proofreading with AI is ordinary. That
is only honest if the member sees and approves the *exact* wording before it is
saved. This screen is what makes the whole provenance model truthful.

It must let the member see and act on:

- the exact final wording that will be saved — reviewable and directly editable;
- its classification (Work / Personal / Both), changeable here;
- its source attribution;
- its AI-use permission, with the default visible and changeable;
- **`Save privately`** as the single primary action;
- `Keep working` and `Save unfinished` as honest exits.

Nothing is saved before this screen. Design it so a member who changes one word
still feels the result is theirs.

---

## 3. Required correction — screen 04's destination card

**Superseded by owner decision, 2026-08-01: PeerSlate does not create résumés.**

`Create a résumé bullet` / `Create résumé draft` must go. Pete's words: we are
not making résumés, we are updating what we already have on the site, and we are
not competing with word processors or résumé-builder sites. This also returns
the design to the page-purpose inventory he already approved on 2026-07-24,
which records this as a "resume-page content update … not a template builder."

What replaces it: an offer to **update something that already exists on the
member's PeerSlate site** — their résumé page content, My Story, or the Feed —
by explicit choice. It prepares; the destination still owns final approval.

Two further requirements for that card:

1. **Demote it.** It is currently the strongest element on the screen and sits at
   the flow's visual conclusion, competing with the message that the private save
   is already a complete success. The save is the win. `Close for now` deserves
   honest standing beside it.
2. **Design a "coming later" variant.** The first release ships the knowledge
   base without destination writes, because the résumé and My Story currently
   render from fixture files with no write target. The saved state needs an
   honest not-yet-available treatment as well as the live one — not a hidden
   control, and not a button that pretends.

---

## 4. Other corrections

**Material — these change composition, so they are yours to resolve:**

| # | Screen | Problem |
|---|---|---|
| 1 | 04 / 05 | The same item's saved wording differs between screens with no visible cause. As drawn it implies silent rewriting. Make the saved text identical across screens |
| 2 | 02 / 03 | `Back to skills` implies a skill-selection state that does not exist in the set. Either draw it or correct the label |
| 3 | 02 | A large central microphone floats above an active Type tab with a text editor — two competing entry metaphors live at once. The Type/Speak tabs should govern the mode |
| 4 | 03 | `Add the missing result` is primary but leads nowhere near saving, and it appears to duplicate the inline answer box under `One useful question`. One primary should advance toward the new final-review screen; enhancement actions sit below it |
| 5 | 04 | Privacy and AI-use reassurance is stated three to four times — left rail, item card, and both right-rail cards. Consolidate |
| 6 | 05 | Area filters (All/Work/Personal/Both) and status filters (Confirmed/Suggested/…) share one chip style, and status chips carry semantic colour, so `All`, `Confirmed`, and `Suggested` can all read as active at once. Selection must be unmistakable and not colour-dependent; semantic colour belongs on item badges |
| 7 | 01 | The Spark card and the `Why this suggestion` rail state the same grounding twice |
| 8 | 01 | Two primary actions compete (`Work on this` and `Continue`) |

**Polish:** "…strengthen your story" on screen 04 risks reading as the My Story
product; `Not currently used elsewhere` and `Private` appear to mean the same
thing in the screen 05 list; the footer privacy line appears on screens 01–03
then disappears; `Back to session` after a completed save has no clear
destination.

---

## 5. States and viewports still missing

None of these exist yet, and implementation evidence cannot be produced without
them:

- **Responsive:** desktop and mobile for every screen, including the new
  final-review screen. Define the three-rail collapse order.
- **First run / empty:** a member with no confirmed information — what grounds
  the Spark and the rails when there is nothing yet? This must be honest, not a
  fabricated suggestion.
- **AI unavailable:** the library, direct entry, editing, and saving all keep
  working; only the AI panels degrade. This needs a real design, not a spinner.
- **Loading, error, permission denied.**
- **Voice:** recording, transcribing, retry, and microphone-permission-denied.
- **`Use as context`:** selected, unselected, and unavailable (when an item's
  AI-use permission is off).
- **Empty library, archived view, and the affected-use review** when an item that
  is already in use changes.
- **Accessibility:** visible focus, 200% zoom, 320 px reflow with no horizontal
  scroll, reduced motion.

---

## 6. Constraints and open items

- **Navigation:** the nav in both the candidate screens *and* the reference
  screenshot does not match the live site. The real header is Pete's Slate ·
  Community · Interview Studio. Pete's decision: Workshop sits **next to
  Interview Studio**, and Interview Studio is not renamed or removed. Draw the
  real navigation plus Workshop, not the placeholder set.
- **Do not draw a decided URL.** The browser chrome in the candidates reads
  `peerslate.com/workshop`; the actual route is an open architecture decision.
  Omit the chrome or keep it neutral so the mockup does not silently decide it.
- **`View private profile`** is generated placeholder language and is not an
  accepted replacement for the current profile control.
- **Naming:** the surface stays **Workshop** for now. Pete anticipates a later
  rename to **My Slate** — do not design anything that depends on the word.
- **Style:** professional, calm, contemporary, trustworthy; AI-centric without
  becoming a chat transcript. Navy, glassmorphism, neon, card-wall dashboards,
  gamification, and decorative excess remain rejected. Palette and background
  strength stay deferred unless Pete decides them this round.
- **Consistency:** the prior set mixes 1280×910 JPEGs with browser frames and
  ~1487×1058 PNGs. Comparable states should be comparable.

---

## 7. What to return

1. The corrected five screens plus the **new final-review / Save privately
   screen**, at consistent dimensions.
2. The responsive and state set from §5.
3. A short note on anything in §4 you resolved differently and why — a better
   answer than the one implied here is welcome; these are findings, not
   specifications.
4. A manifest with SHA-256 for every file, so Pete can lock exact hashes.

Then Pete locks the exact files and hashes, and only then does implementation
begin.
