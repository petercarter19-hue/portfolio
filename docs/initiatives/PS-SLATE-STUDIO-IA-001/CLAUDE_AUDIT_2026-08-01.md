> **Supersession note (added on package-copy, 2026-08-01).** This audit is
> preserved as dated evidence exactly as returned to Pete. Two of its
> recommendations were subsequently decided differently by the owner and are
> superseded by `16_OWNER_DECISION_RECORD_WORKSHOP_2026-08-01.md`:
>
> 1. Finding **C2** proposed labelling accepted AI refinements in the source
>    line (e.g. "Your words, refined with AI"). Pete decided **not** to label
>    them; the member-approved wording is canonical and unlabelled, made honest
>    instead by the explicit save-consent state that finding **C1** requires.
> 2. Question **5** and finding **M5** assumed a résumé-draft destination. Pete
>    decided PeerSlate does **not** create résumés; downstream use updates
>    existing site surfaces only.
>
> All other findings stand as written.

# Workshop handoff — Claude independent audit

**Date:** 2026-08-01
**Auditor:** Claude Code (product, interaction, trust, and consistency audit only — no implementation authority)
**Package reviewed:** `PeerSlate Workshop Claude Handoff 2026-07-31.zip` (ChatGPT → Claude)
**Repository grounding:** Azure `origin/main` fetched 2026-08-01 at `2494aa73ed95bfbe97d8cf42f712b9929759e0b2` — identical to the SHA the handoff verified on 2026-07-31. Active package `PS-SLATE-STUDIO-IA-001`, status `visual_direction_only_no_runtime_authority`.
**Integrity:** All six image SHA-256 hashes recomputed and matched `SHA256SUMS.txt` and the visual manifest exactly.
**Authority status honored:** These are structurally accepted candidates, not a Pete-locked implementation authority. Nothing in this audit treats them as approved for code, implemented, or live.

---

## 0. Restatement of the direction under review

Workshop is one authenticated, private, AI-centric surface where a member adds, strengthens, reviews, and controls information about themselves through small units of work. It has two modes on one surface: **Work on Something** (AI-assisted contribution and improvement of one useful thing) and **My Information** (the member-controlled private library: search; Work/Personal/Both lenses; Confirmed/Suggested/Unfinished/Archived states; direct entry and editing; provenance; per-item AI-use permission; current-use review; archive and delete).

Four data classes stay permanently distinct: (1) member source words, (2) AI interpretation or suggestion, (3) confirmed private information, (4) purpose-specific use (a separate résumé, Feed, or public-profile draft created only by explicit member action). The model is `Contribute → review → confirm privately → optionally create a separate use` — never `AI infers → silently saves → silently publishes`.

The five-screen workflow: **Opening** (one grounded Spark, direct type/speak entry, four starting paths, unfinished work) → **Type/Speak session** (one focused question; confirmed items offered as session-scoped `Use as context`) → **AI Review** (original wording preserved; interpretation shown separately; what's strong; one standout piece of evidence; one thing worth strengthening; one follow-up question — no grading) → **Saved Privately** (explicit save; "Nothing was added to your résumé, Feed, or public profile"; only then one optional destination-specific draft offer) → **My Information** (the second mode, not a mandatory linear step).

This direction deliberately resets parts of the older Workshop/Slate Studio discussion (Journal is not a near-term dependency; whiteboard and Goal Board are back-burnered; destinations are limited to résumé, Feed, and public profile). It is newer conversation-level owner direction, not yet reconciled into repository governance, and this package grants no implementation authority.

---

## 1. Overall verdict

**The product direction is sound and internally coherent, and the candidate set is close — but it is not lockable yet.** The set's greatest strength is that it makes the four-class data model *visible* (especially on the AI Review screen). Its two Critical defects are both trust defects at the single most important moment of the product: the explicit private-save consent step is missing from the visual sequence, and the saved item's provenance label misattributes AI-refined wording as the member's own words. Both directly contradict the written direction the set is meant to express. One focused ChatGPT correction round plus Pete's answers to five questions should get the set to lock quality.

---

## 2. What is strongest and should remain

1. **AI Review's original-vs-interpretation separation (Screen 03).** "Your original wording" (editable) above "PeerSlate's interpretation" (visually distinct) is the best screen in the set — it operationalizes the data-class model as UI, not just policy.
2. **The review rhythm without grading.** Strong points → one standout piece of evidence → one thing worth strengthening → one useful question. It borrows Interview Studio's satisfying contribute/review/improve loop with no score, no "3 of 10", no deficit framing. The star reads as "useful evidence," not a reward.
3. **The suggestion card on My Information (Screen 05).** "SUGGESTED BY PEERSLATE — NOT CONFIRMED", an explicit evidence citation ("Based on: Systems Engineering"), and Review / Edit and confirm / Dismiss / Do not suggest this again is exemplary AI-boundary UI. This card should become the template for every AI proposal in the product.
4. **Downstream-truth banner (Screen 05).** "This information is used in your résumé draft. Changing it here will not silently change that draft." Exactly the promised behavior, stated at exactly the right moment.
5. **Negative-space save confirmation (Screen 04).** "Saved privately. Nothing was added to your résumé, Feed, or public profile." Telling the member what did *not* happen is the strongest trust copy in the set.
6. **Session-scoped context boundary (Screens 02/03).** "Use as context … adds context to this private session. It does not change or confirm the underlying information."
7. **The calm three-rail studio composition,** serif/sans hierarchy, and complete absence of gamification, streaks, completeness meters, or identity homework. The written direction's tone is genuinely achieved.
8. **Spark grounding.** "Based on information you've confirmed" plus a plain-language explanation of what PeerSlate noticed, with "Show another idea" as a pressure-free exit.

---

## 3. Prioritized mismatch register

### Critical

**C1 — The explicit "Save privately" consent state is missing from the sequence.**
The written direction defines the trigger to Screen 4 as: "the member reviews the final proposed private information and explicitly selects `Save privately`." No screen shows that state or that control. Screen 03's actions are Edit myself / Save unfinished / Stop for now / Improve with AI / Add the missing result — none reaches Screen 04. The single most important consent moment in the entire trust model is undrawn, and the workflow is not visually continuous without it. A sixth screen (or a defined final state of Screen 03) must show: the exact final proposed wording, its classification, its source attribution, its AI-use permission default, and the explicit `Save privately` action.

**C2 — Saved-item provenance is misattributed, collapsing AI refinement into member truth.**
The member's original words (Screens 02/03): "I brought our product, hardware, and software teams together to define the architecture…". The saved item (Screen 04) reads "Led cross-functional product, hardware, and software teams in defining a next-generation system architecture…" — a third, AI-polished formulation that is neither the original nor the shown interpretation — yet its Source row says "Your words from this Workshop session." Screen 05 repeats the pattern. This is precisely the forbidden failure: collapsing source words and AI interpretation into one truth. Fix requires both a flow answer (C1's final-review state is where the member sees and approves the exact wording) and an honest label (e.g., source = "Your words, refined with AI — approved by you", with the original always retained and inspectable).

### Material

**M1 — Same item's "member-approved wording" differs again between Screens 04 and 05** with no visible cause. Even if the in-world explanation is "the member edited it" (edit history shows 3 changes), a candidate set for lock must show identical saved text across screens; as drawn it visually implies silent rewriting.

**M2 — "Back to skills" (Screens 02/03) implies an undrawn intermediate skill-selection state.** Either the label is wrong or a state is missing between Opening and the session. Workflow continuity must be explicit before lock.

**M3 — Type/Speak dual affordance conflict (Screen 02).** A large central mic ("Tap to start speaking") floats above an active Type tab with a text editor. Two competing entry metaphors are live at once. The Type|Speak tabs should govern the mode; the mic belongs inside Speak mode. (The Interview Studio reference gets away with this because the mic is the poster affordance; here it fights the tabs.)

**M4 — Primary-action hierarchy on AI Review (Screen 03).** "Add the missing result" is the primary CTA, and there is no visible path toward save (see C1). Recommended rule: one primary that advances toward the final review/save moment; "Improve with AI" and "Add the missing result" are enhancement branches at secondary weight. (Also: "Add the missing result" and the inline answer box under "One useful question" appear to be two controls for the same action — clarify.)

**M5 — Destination-draft dominance on Saved Privately (Screen 04).** "Create résumé draft" is the strongest CTA on the screen and sits at the flow's visual conclusion, competing with the message that the private save is already a complete success. Demote to secondary/offer weight and give "Close for now" honest equal standing.

**M6 — Privacy/AI-use reassurance is stated three-to-four times on Screen 04** (left rail "Where it's available", the item card's AI-use row, and both right-rail cards). Consolidate: item-level truth on the card once, one page-level reassurance.

**M7 — My Information filter chips conflate two filter groups and status colors (Screen 05).** Area lens (All/Work/Personal/Both) and status (Confirmed/Suggested/Unfinished/Archived) share one chip style while status chips carry semantic green/orange, so All + Confirmed + Suggested read as simultaneously active. Selection must be shape/fill-based and color-independent; semantic colors belong on item badges, not filter controls.

**M8 — Blanket source line under Related information (Screens 02/03) is ambiguous** ("Source: Your words from this Workshop session" sits beneath a list of items whose actual sources vary). Provenance must be per-item.

**M9 — Missing states acknowledged by the manifest, required before implementation:** first-run/empty (no confirmed information — what grounds the Spark and the rails?), loading, error, AI-unavailable (core page must stay usable: direct entry, editing, and the library work without AI), permission-denied, voice recording/transcribing/retry, `Use as context` selected/unselected/unavailable, the post-"Create résumé draft" result state, archive/delete confirmation + restore, and the affected-use review flow.

**M10 — Rich-text toolbar in the member-source editor (Screen 02: bold, italic, lists, link).** Formatted canonical member source raises provenance and downstream-rendering questions (a résumé bullet will not carry bold/links). Recommend plain text for v1; if formatting stays, its downstream behavior must be specified. (Pete decision — Q3.)

**M11 — Voice/persona copy inconsistency.** "Tell me about a situation…" and "We'll listen" (Screen 02) imply a first-person someone, while every other screen correctly speaks as PeerSlate ("Tell PeerSlate…", "Here's what PeerSlate heard"). The direction says Spark is not a personality; standardize on PeerSlate-as-actor.

### Polish

**P1 —** Spark card and "Why this suggestion" rail on Screen 01 restate the same grounding twice (manifest concern confirmed). Merge, or make the rail progressive detail.
**P2 —** Two primaries on Screen 01 ("Work on this" and "Continue"); "Continue" should be disabled/secondary until the member types or speaks.
**P3 —** "…strengthen your story" (Screen 04 right rail) risks reading as the My Story product, which is explicitly out of scope this round. Reword ("how you present yourself").
**P4 —** Use-line copy inconsistency in the Screen 05 list: "Not currently used elsewhere" vs "Private" appear to mean the same thing.
**P5 —** Footer privacy line appears on Screens 01–03 and disappears on 04–05; unify placement.
**P6 —** Mode-specific subtitles (Opening vs My Information) — confirm intended; if so, keep both stable.
**P7 —** "Back to session" (Screen 04 left rail) is ambiguous after a completed save — define its destination.
**P8 —** At lock time, confirm the accent blue is deliberately distinct from the rejected navy environment direction, and that orange "Suggested" text and small gray captions meet 4.5:1 contrast on the pale gray-blue field.
**P9 —** Known set inconsistencies (already governed by the manifest): mixed dimensions/browser chrome; placeholder global navigation; "View private profile" placeholder. Not accepted by inference; resolved at the lock pass and by Pete's navigation decision (Q4).
**P10 —** The standout-evidence star is acceptable as drawn (single instance, labeled, not a score). Keep it to exactly one per review; revisit only if it starts reading as a reward.

---

## 4. Screen-by-screen audit

### Screen 01 — Opening
Composition and intent are right: one Spark, direct entry, four starts, unfinished work, all in the three-rail rhythm. Grounding chip and explanation are excellent. Issues: P1 redundancy with the right rail; P2 dual primaries; behavior rules needed for Spark frequency, dismissal memory, and the no-confirmed-information first run (M9). "Show another idea" honors the no-nagging rule; the spec must make dismissal durable.

### Screen 02 — Type/Speak
The focused-question format, `Use as context` boundary copy, "Both build the same answer" type/voice parity, character budget, and Save unfinished are all correct. Issues: M2 ("Back to skills"), M3 (mic vs tabs), M8 (blanket source line), M10 (rich text), M11 (voice copy). The written direction lists "stop" as a member option here, but only Screen 03 draws "Stop for now" — add it or define closing behavior. Switching starting paths mid-session (left rail stays active) needs a defined save-or-discard prompt.

### Screen 03 — AI Review
The best screen; see Strengths 1–2. Issues: C1 (no path to save), M4 (CTA hierarchy), and the "Improve with AI" action needs definition: what it rewrites, where its output lands, and how it is labeled (it must produce a *proposal* the member accepts, never an in-place rewrite). Answering the follow-up question should visibly loop the review (updated interpretation/strengths) rather than dead-end.

### Screen 04 — Saved Privately
Confirmation copy is exemplary; the metadata rows (Classification / Source / AI use) are the right minimum. Issues: C2 (source mislabel), M1 (wording drift), M5 (draft-offer dominance), M6 (reassurance redundancy), P7 ("Back to session"). The destination offer correctly appears only after the save completes — preserve that sequencing exactly. The post-draft-creation state (where the member lands, what the draft's status is, and the "final approval remains in the destination" handshake) is undrawn (M9).

### Screen 05 — My Information
Correctly a private library, not Settings: no account/security content, per-item AI-use permission, current uses, edit history, archive/delete, and the affected-use banner are all right. The suggestion card is the set's best AI-boundary component. Issues: M7 (filter states), M1/C2 (wording/provenance), P4 (use-line copy). Search, sort, "Showing 4 of 4" are fine. Empty library, archived view, restore, and delete-with-affected-uses flows are undrawn (M9).

---

## 5. Interaction specification (behavioral level only)

### 5.1 Modes and global structure
- One authenticated route surface with two modes: `Work on Something` and `My Information`. Mode switch is a top-level tab pair; switching modes never discards session work (an active session persists as Unfinished).
- Every screen keeps the member's exit rights visible: save unfinished, stop, or navigate away — none of which loses text.
- All Workshop content is private to the authenticated owner. Identity is server-derived; every read/write is authorized server-side. No Workshop data appears in any public or connection-visible surface.

### 5.2 Core objects (behavioral, not schema)
- **Item** — one unit of member information. Properties: title; current member-approved wording; classification (Work / Personal / Both / unclassified); state (Confirmed / Suggested / Unfinished / Archived); provenance chain; AI-use permission (allowed / not allowed for private suggestions); current uses (references); edit history.
- **Provenance chain** — the original member source (typed text or voice transcript) is retained verbatim and inspectable for the life of the item. Every AI refinement the member accepts is recorded as a distinct step ("refined with AI, approved by member on date"). The original is never overwritten.
- **Session** — one Work on Something engagement: starting path, focused question(s), member answer text, `Use as context` selections, AI review artifacts. Sessions are private, resumable, and produce at most one saved item (v1).
- **Suggestion** — an AI-proposed item or addition. Always labeled unconfirmed; always cites the confirmed member evidence it is based on; never counted as member information until explicitly confirmed.
- **Destination draft** — a separate object created only by explicit member action after a private save, referencing the exact item version it was drafted from. Editing the item later never silently changes the draft; the destination owns final approval.

### 5.3 State transitions (member-visible)
1. **Opening → Session:** via `Work on this` (Spark), a starting path (with an intermediate chooser state where a path needs one, e.g. skill selection — resolves M2), `Continue` on an unfinished item (restores all session state), or submitting an open thought.
2. **Session → Review:** `Review what I shared` (disabled until the member has contributed content).
3. **Review loop:** answering the follow-up question or accepting an `Improve with AI` proposal re-renders the review with updated content; the member may loop any number of times, or `Edit myself` at any point.
4. **Review → Final review (new state, resolves C1):** one screen/state showing the exact proposed saved item — final wording, classification (editable), source attribution (honest per C2), AI-use permission default — with `Save privately` as the single primary action and `Keep working` / `Save unfinished` as exits.
5. **Final review → Saved Privately:** only on explicit `Save privately`. The item becomes Confirmed. Confirmation states what did not happen.
6. **Saved Privately → optional destination draft:** one offer, secondary weight (resolves M5). `Create résumé draft` creates the draft, shows a created state naming where final approval happens, and links there. Declining ("Close for now") returns to Opening with no follow-up nagging.
7. **My Information** is reachable at any time and never a forced step.

### 5.4 AI behavior rules
- **Spark:** at most one on Opening; grounded only in Confirmed items whose AI-use permission is allowed; always states its grounding; `Show another idea` cycles; dismissal is remembered and the same Spark is not repeated; no Spark exists → honest neutral opening (first-run state), never a fabricated one.
- **`Use as context`:** per-item toggle, off by default, session-scoped, visibly selected/unselected; unavailable (with reason) when an item's AI-use permission is not allowed. It never confirms, edits, or reclassifies the underlying item.
- **`Improve with AI`:** produces a labeled proposal shown beside (never replacing) the member's text; member accepts, edits, or discards; acceptance is recorded in provenance.
- **Review content:** interpretation, strengths, standout evidence, one improvement, one question — grounded only in what the member shared plus selected context. No scores, no completeness meters, no deficit language, no sensitive-attribute inference the member did not initiate.
- **Suggestions in My Information:** evidence-cited, dismissible, with `Do not suggest this again` honored durably.
- **AI unavailable:** Opening (minus Spark), direct entry, editing, the library, and — importantly — saving privately all keep working. AI-dependent panels show an honest unavailable notice, never skeleton fakes. Direct entry means a member can create and confirm an item with no AI step at all.

### 5.5 Save, edit, and downstream truth
- Saving is always explicit, always preceded by the final-review state, and always followed by the negative-space confirmation.
- Editing a Confirmed item creates a new version in edit history; provenance persists; current uses are unaffected until the member reviews them (affected-use review lists each use and offers per-use update — never bulk-silent).
- Archive is reversible, removes the item from AI grounding, and keeps it out of lenses by default. Delete requires confirmation, and when uses exist, the affected-use review runs first. Neither ever silently edits a destination.
- AI-use permission changes take effect immediately for all future AI grounding.
- Unfinished work autosaves as the member types/speaks (private, owner-only), appears under Continue and in the Unfinished lens, and restores completely.

### 5.6 Voice
- Speak mode records, transcribes, and places the transcript into the same editable field as typed text ("both build the same answer" — the member always sees and can edit the transcript before it is treated as their words). Recording, transcribing, error, retry, and microphone-permission-denied states are explicit. Raw audio handling/retention is an architecture decision to be made deliberately (recommend: transcript is the member source; audio is not retained in v1).

---

## 6. Trust and data-boundary audit

| Boundary | Verdict |
|---|---|
| Private by default; nothing publishes implicitly | **Pass as drawn** — footer line, save confirmation, and library copy all state it; keep server enforcement in architecture |
| Member source vs AI interpretation kept distinct | **Pass on Screen 03; FAIL at save (C2)** — the misattributed source label is the set's most serious defect |
| Explicit member consent to save | **FAIL as drawn (C1)** — the consent state is undrawn |
| AI proposes, member decides | **Pass** — suggestion card, `Use as context`, draft offer are all explicit-action patterns |
| One authoritative source per fact; uses are references | **Pass in intent** — "Used in:" plus the no-silent-change banner imply destination drafts pin an exact item version; make version-pinning explicit in architecture |
| No grading/deficit framing | **Pass** — no scores anywhere; language stays constructive |
| No nagging after dismissal | **Pass in copy ("Do not suggest this again"); needs durable behavioral rule** |
| Bounded promise (not "everything PeerSlate knows") | **Pass** — Screen 05 header says "information you have chosen to give PeerSlate" |
| My Information ≠ Settings | **Pass** — no account/security content present; keep it that way |
| Multi-member reusability | Fixture content is Pete-only (correct for mockups); architecture and tests must be generic-member from the start |

---

## 7. Accessibility and responsive requirements not yet shown

1. **Keyboard:** complete flow operability — mode tabs, starting paths, `Use as context` toggles (with pressed state), filter chips (selection exposed to AT), suggestion-card actions, and `Save privately` all reachable and operable; visible focus everywhere; no keyboard trap in the voice UI.
2. **Voice parity:** typing is the built-in equivalent for every voice action (already the direction); microphone-permission-denied has a first-class state.
3. **Color independence:** Confirmed/Suggested/etc. must never be color-only (text labels already present — keep them); filter selection must be shape/fill-based (M7).
4. **Contrast:** orange Suggested text, light gray metadata/captions, and blue-on-pale-gray-blue accents verified ≥ 4.5:1 at lock time.
5. **Reduced motion:** mic pulse and any transition animations honor `prefers-reduced-motion`.
6. **Zoom/reflow:** 200% zoom and 320 px-wide reflow with no horizontal scroll; define the three-rail collapse order (recommend: workstage first, starting rail as collapsed menu, context rail last).
7. **Screen readers:** AI-generated regions labeled as such; save confirmation announced via live region; review sections as real headings; the suggestion card announced as unconfirmed.
8. **Touch targets:** `Use as context`, filter chips, and rail links currently render as small text links — minimum 24 px targets.
9. **Long content:** 1000-character answers, long titles, and large libraries (list virtualization/pagination is an architecture concern; visually, define overflow behavior).
10. **Responsive set:** desktop and mobile production-intent visuals for at least Opening, Session, Review, Final review/Save, Saved, and My Information are required before implementation evidence can exist (per the visual standard).

---

## 8. Non-material corrections vs material changes vs Pete decisions

**Non-material (implementable later within a locked visual, documented as adaptations):** P4, P5, P8 contrast/touch-target verification, M8 per-item source metadata, M11 copy standardization, adding undrawn accessibility states that follow the locked composition (focus styles, reduced motion, reflow), and honest state wiring (loading/error/unavailable) that doesn't change composition.

**Material — must return to the ChatGPT visual lane and Pete for a corrected lock:** C1 (new final-review/Save privately state — a new screen), C2 (provenance labeling on 04/05), M1 (stable saved wording across screens), M2 (skill-selection state or label fix), M3 (type/speak affordance unification), M4 (Screen 03 CTA hierarchy), M5 (Screen 04 draft-offer weight), M6 (reassurance consolidation), M7 (filter selection treatment), P1/P2 if Pete agrees (composition-level), plus the manifest's own open items: comparable dimensions/chrome, and the responsive/state set (M9) to the extent those states are new compositions.

**Pete decisions (product/architecture, not visual):** the five questions below, plus at architecture time: audio retention policy, versioning/edit-history depth, and Workshop's relationship to the released default-off Slice 1 Studio route.

---

## 9. Questions for Pete (max five)

1. **The save moment and canonical wording (decides the data model — answer needed before architecture).** Confirm a distinct final-review state with explicit `Save privately` (C1). And when the member accepts an AI refinement: is the canonical saved wording (a) the member's original words, with the accepted refinement stored as a labeled display form — or (b) the member-approved refined text as canonical, with the original retained as inspectable provenance? (I recommend (b): the approved text is what the member chose, and provenance keeps the truth chain.)
2. **AI-use permission default at save.** The mockups show "Available for private PeerSlate suggestions" as the default. Keep allowed-by-default with per-item opt-out, or ask at the final-review moment each time? (I recommend allowed-by-default shown explicitly at final review — visible, changeable, bounded to private suggestions.)
3. **Member-source formatting.** Plain text only in v1 (my recommendation), or keep the rich-text toolbar (bold/lists/links) with defined downstream-rendering rules?
4. **Navigation and route reality.** Where does Workshop actually live in navigation (alongside Living Résumé and Interview Studio, which the placeholder nav drops), what happens to "View public page" vs the generated "View private profile", and is Workshop the evolution of the released default-off Slice 1 protected Studio route (reuse/replace) or a separate new route?
5. **Post-save destination offer weight.** Should the destination draft offer be demoted to a quiet, co-equal option ("your save is complete; if you want, PeerSlate can also draft…" — my recommendation, resolves M5), or remain a prominent primary next step?

---

## 10. Recommended next gate

**Gate: ChatGPT visual-correction round → Pete exact lock → governance reconciliation → architecture package.**

1. Pete answers the five questions (Q1 unblocks architecture; Q4 unblocks navigation/route planning).
2. The Critical and Material register items return to the ChatGPT visual-creation lane for one correction round, including the new final-review/Save-privately screen. Claude does not create these visuals.
3. Pete locks the corrected exact set — files plus SHA-256 hashes pinned in `PS-SLATE-STUDIO-IA-001` — with the palette/background decision made or explicitly deferred with the locked set as binding minimum.
4. A documentation-only governance PR reconciles the new Workshop direction into the repository (owner direction record; supersession notes against package docs 12–15; baseline status update), since this direction currently exists only at conversation level.
5. Claude writes the non-visual product/technical architecture as a bounded package deliverable (data model with provenance/versioning, state machine, route/API contracts, server-derived authorization, AI service boundaries, degradation modes, test strategy). Sections 5–7 of this audit are its behavioral seed. Entry per `START_HERE.md`: named manager, single writer, fresh `work/` branch from current `origin/main`.
6. Implementation follows in slices (private library + direct entry first; session/save; AI review; Spark; destination drafts), each with the required evidence, visual parity, accessibility checks, and release gates. Note: the open PS-OPS Candidate-admission correction must land before any next Candidate-based release.

**Stopping point honored:** per the handoff, this audit stops here. No mockups were created, no repository files were changed, and nothing above claims any Workshop behavior is implemented or live.
