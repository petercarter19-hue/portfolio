# Disposition matrix (PROPOSED)

> **STATUS: PROPOSED.** Complete Locked / Open / Later / Tabled / Rejected-current
> classification for every connective and retention idea in the source handoff,
> per Section 12.11 of that handoff and candidate requirement
> `PS-CORE-GOV-008`.
>
> **Preservation is not authorization.** Nothing in the Locked column is
> implemented, assigned, deployed, enabled, or live. Locked means the *direction*
> is decided, not that any code exists.

## Status meanings

Taken from Bible v2.6 "Status language," unchanged.

| Status | Meaning |
|---|---|
| LOCKED | Approved governing direction; change requires an explicit decision and recorded rationale. |
| OPEN | A material decision is unresolved; no implementation assumption may silently close it. |
| LATER | Compatible with the vision but outside the current build sequence. |
| TABLED | Preserved but with no current design, prototype, or build authorization. |
| REJECTED-CURRENT | Conflicts with current principles or sequencing. Not necessarily banned forever; rationale is in the Decision Register. |

---

## 1. LOCKED / current direction — 12 items

| # | Decision | Where it is encoded |
|---|---|---|
| L1 | Every page should feel like a different use of the same life. | Bible §Executive direction; §19 Locked |
| L2 | Stronger trunk, not more branches. | Bible §Executive direction; PS-P-015 |
| L3 | Focused rooms connected by a visible spine. | PS-P-015; §6 connected-room contract |
| L4 | Create once, place many through canonical references. | B26 §5 unchanged; PS-CORE-DATA-007 |
| L5 | Same interaction grammar, mode-aware authorized payload. | PS-CORE-IA-014 |
| L6 | One best bridge, no wall of recommendations. | PS-CORE-IA-015 |
| L7 | Relationship before promotion. | Bible §5 "Relationship before promotion" |
| L8 | Temporal continuity through memory, Replay, and useful next steps. | PS-CORE-IA-016; §6 temporal spine |
| L9 | Momentum hooks, not pressure hooks. | PS-P-016; PS-CORE-VAL-005; §11 |
| L10 | Expression-first, modality-flexible voice and text parity. | §9; PS-CORE-FR-010 |
| L11 | Return value stays private-first, source-linked, finite, dismissible, non-diagnostic. | PS-CORE-VAL-005; PS-CORE-AI-007 |
| L12 | The proof graph is an outcome of canonical placement, not a new product truth. | Bible §12; Architecture §5 |

---

## 2. OPEN decisions — 11 items, all preserved unresolved

**None of these was closed, narrowed, answered, or implied by this package.**

| # | Open decision | Who must decide | Why it is still open |
|---|---|---|---|
| O1 | Exact visual form and canonical name of the Slate Spine. | Pete, with a designated visual manager | Requires a production-intent mockup and visual acceptance under `OWNER_VISUAL_INTEGRITY_STANDARD.md`. "Slate Spine" is a working label only. |
| O2 | Whether the first public pilot is a new package or an amendment to active Resume/Studio packages. | Pete and the designated session manager | `PS-HOME-INTERVIEW-PARITY-001` is mid-lane; reopening an active package is a manager sequencing decision, not a writer decision. |
| O3 | Which three to five Resume achievements receive Backstory Drawers. | Pete | Content and public-safety judgment about specific claims. |
| O4 | Whether public Studio support is curated configuration or projection-backed after canonical services mature. | Architecture decision at the pilot's entry gate | Depends on whether projection services exist by then. |
| O5 | Exact owner-mode Return Ticket actions and storage. | Deferred to the owner-mode package | Requires the Owner Home frontend and a persistence decision that does not exist yet. |
| O6 | Exact cadence and user controls for Replay and resurfacing. | Pete, with Phase 9 architecture | Cadence is a member-trust decision, not a default. |
| O7 | Whether Focus Themes are fixed, member-authored, AI-suggested, or hybrid. | Pete | Each option has different AI-governance and privacy consequences. |
| O8 | Whether Progress Keepsakes live inside Replay, My Slate, Story, or a private collection view. | Pete | Placement determines whether it risks becoming a destination. |
| O9 | Whether a soft consistency visualization is useful without becoming a streak. | Pete | Sits directly on the PS-P-016 boundary; needs evidence, not assertion. |
| O10 | Notification policy, channels, timing, and opt-in defaults. | Pete | No notification system exists or is assumed. Defaults are a trust decision. |
| O11 | Raw-audio retention and voice-processing disclosures. | Pete, with privacy review | `PS-VOICE-001` retains private original audio; the durable retention policy and disclosure text are not settled. |

---

## 3. LATER — 10 items

Compatible with the vision, outside the current build sequence.

| # | Item | Gating condition |
|---|---|---|
| LT1 | Then and Now across Home, Story, Studio, and Work | Mature confirmed history, source authorization, contradiction handling, correction behavior |
| LT2 | Focus Themes | The return loop is proven first |
| LT3 | Progress Keepsakes | The return loop is proven first |
| LT4 | Prompt DNA | Enough history and model-governance evidence |
| LT5 | Signal Cards | Enough history and model-governance evidence |
| LT6 | Guided journeys or challenge-free challenges | Must have no failure state; return loop proven first |
| LT7 | Future Me text or voice messages | Voice trust and retention behavior proven |
| LT8 | Walk-and-Talk, Story Mode, Duet With Your Past Self, Voice Keepsakes, private growth reels | Transcript, review, privacy, retention, and failure behavior proven |
| LT9 | Companion / worldbuilding prototype | Retention measured first |
| LT10 | Buddy Reflection | The two-person trust loop proven first |

---

## 4. TABLED — 9 items

Preserved for reconsideration. No current design, prototype, architecture,
backlog, or release authorization.

| # | Item |
|---|---|
| TB1 | FitSlate *(already tabled in v2.6; carried forward unchanged)* |
| TB2 | Literal pet companion |
| TB3 | Garden, constellation, path, room, studio, or archive that grows with contribution |
| TB4 | Public or connection-visible consistency |
| TB5 | Social accountability beyond one trusted person |
| TB6 | Private circles, prompt swaps, or shared themes |
| TB7 | Mood Soundprint or prosody visualization |
| TB8 | Celebration readback |
| TB9 | Ambient soundscape rituals |

---

## 5. REJECTED for the current program — 16 items

Rationale preserved in `05_DECISION_REGISTER_ENTRY.md`.

| # | Rejected item | Principle it conflicts with |
|---|---|---|
| RJ1 | Hard or loss-framed streaks | PS-P-009, PS-P-016, PS-CORE-VAL-005 |
| RJ2 | Points, badges, levels, public consistency counts, trophy cabinets | PS-P-001, PS-P-009 |
| RJ3 | Confetti as the default reward | B26 "Quiet completion" |
| RJ4 | Guilt reminders, "you are falling behind," punitive recovery | Member service covenant; PS-P-016 |
| RJ5 | Infinite feeds, trending modules, popularity ranking, variable-reward rails | PS-P-009; §10 Feed role |
| RJ6 | Generic "Explore more" / "You may also like" without a meaningful relationship | §5 Relationship before promotion; PS-CORE-IA-015 |
| RJ7 | A universal AI sidebar or separate global Insights/Engagement destination | PS-P-014; PS-CORE-IA-005; navigation rule |
| RJ8 | Automatic Resume, Story, Project, Feed, or public publication from Capture or AI | PS-P-010; PS-CORE-AI-001; PS-CORE-FR-005 |
| RJ9 | Room-specific copied facts or separate Resume/Story/Studio truth stores | CANONICAL-TRUTH RULE; PS-CORE-DATA-001; PS-CORE-DATA-007 |
| RJ10 | Emotional diagnosis, mental-health inference, certainty claims from voice prosody | PS-P-005; §9 voice rule; PS-CORE-AI-003 |
| RJ11 | Indefinite raw-audio retention without explicit purpose and member control | PS-P-004; data rights; see O11 |
| RJ12 | Fabricated people, counts, history, activity, insights, or cross-room relationships | PS-P-011; PS-CORE-GOV-003 |
| RJ13 | Turning on disabled or flag-off features through documentation work | Handoff §3; PS-CORE-GOV-003 |
| RJ14 | Broad public redesign before the approved entry gate | B26 §11 public convergence entry gate |
| RJ15 | Using social mechanics to compensate for an incomplete owner loop | PS-P-001; Roadmap sequencing |
| RJ16 | Expanding Projects into a task-management suite | Appendix L Projects covenant; §4 boundaries |

---

## 6. Totals

| Status | Count |
|---|---|
| LOCKED | 12 |
| OPEN | 11 |
| LATER | 10 |
| TABLED | 9 (8 new + FitSlate carried forward) |
| REJECTED-CURRENT | 16 |

Every idea in the source handoff appears in exactly one row. No idea was
silently dropped, and no OPEN item was promoted.
