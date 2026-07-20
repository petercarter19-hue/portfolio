# Traceability matrix (PROPOSED)

> **STATUS: PROPOSED.** Crosswalk from research finding → candidate Bible
> principle or requirement → Roadmap phase or package → Experience System or
> Architecture and Data Standard artifact. Every Roadmap and package reference
> below is candidate or planned unless the row says otherwise. No row authorizes
> implementation.

## 1. Source basis

Section 2 of the source handoff names six inputs. Rows below cite them as:

| Key | Source |
|---|---|
| B26 | PeerSlate Company and Product Bible v2.6 |
| R25 | PeerSlate Product Strategy and Architecture Roadmap v2.5 |
| BRIEF | PeerSlate Product and Architecture Brief, July 2026 |
| TECH | PeerSlate Technical Architecture and Release State, July 2026 |
| HOOKS | PeerSlate Hooks and Connected-Site Research Report |
| VOICE | Deep Research Report on Hooks for a Voice-First Journaling and Growth Website |

**Evidence limitation, stated plainly:** BRIEF, TECH, HOOKS, and VOICE are named
in the handoff as the synthesis basis but are **not present in the repository**
at base `531013dd8c1a05e2443becd881a226755f27ca14`. This matrix traces the
findings as the handoff states them. It does not independently verify the four
absent sources. B26 and R25 were read directly from the repository.

## 2. Structural continuity

| # | Research finding | Candidate Bible authority | Roadmap phase / package | Experience / Architecture artifact |
|---|---|---|---|---|
| S1 | Rooms feel like islands even when the data is connected (HOOKS) | PS-P-015; §6 "The connected-room contract"; PS-CORE-IA-013 | Candidate `PS-PUBLIC-CONNECTIVE-001`, Priority 1A | Experience §2 Slate Spine; Architecture §3 `ResolvedRoomContext` |
| S2 | The same component must serve public and owner viewers without leaking (HOOKS, B26 §8) | PS-CORE-IA-014; §6 contract "same grammar, different payload" | Candidate `PS-CONNECTIVE-COMPONENT-001`, Priority 1C | Architecture §3.2 rules 1–7 |
| S3 | Cross-promotion breaks focused task rooms (HOOKS) | PS-CORE-IA-015; §6 "Focused but not orphaned" | Priority 1A scope limit: one primary, two secondary | Experience §1 rules 4–5 |
| S4 | Members need a reason, not a link (HOOKS) | §5 "Relationship before promotion"; rejected-current list | Priority 1A out-of-scope: generic rails | Experience §8 content voice |
| S5 | A résumé claim is more persuasive with its earned context (HOOKS) | §7 Connected-room patterns — Backstory Drawer | Priority 1A, three to five anchor claims | Experience §3 |
| S6 | Practice is most useful when tied to real approved work (HOOKS) | PS-CORE-FR-009; Studio Return Ticket | Priority 1A, public/browser-local truth only | Experience §4 |

## 3. Canonical continuity

| # | Research finding | Candidate Bible authority | Roadmap phase / package | Experience / Architecture artifact |
|---|---|---|---|---|
| C1 | Connection must not fork the facts (B26 CANONICAL-TRUTH RULE) | PS-CORE-DATA-007 | Priority 2: `PS-CAPTURE-002`, `PS-MOMENT-001`, `PS-PLACEMENT-001` — all released | Architecture §5 "No new system of record" |
| C2 | The proof graph is emergent, not a new store (HOOKS, BRIEF) | §12 "No new system of record" | Priority 2 acceptance outcome of `PS-PLACEMENT-001` | Architecture §5 |
| C3 | Correction, deletion, and revocation must propagate to derived views (B26 PS-CORE-DATA-004) | PS-CORE-DATA-007; PS-CORE-NFR-008 deleted-source state | Priority 2 required outcomes | Architecture §3.3; §5 |
| C4 | Relationships must never grant access (BRIEF) | §6 contract hard boundary; B26 authorization-before-retrieval | Priority 2 required outcomes | Architecture §3.2 rule 2; §5 |
| C5 | Relationship labels must derive from governed types (HOOKS) | PS-CORE-DATA-007 | Priority 2 required outcomes | Architecture §4 candidate vocabulary |

## 4. Temporal continuity and return value

| # | Research finding | Candidate Bible authority | Roadmap phase / package | Experience / Architecture artifact |
|---|---|---|---|---|
| T1 | Tiny-entry loop with immediate payoff drives durable return (VOICE) | §7 "The return-value engine"; PS-CORE-VAL-005 | Priority 3, candidate `PS-RETURN-VALUE-001` first slice | Experience §1 rule 9; §8 |
| T2 | Resurfaced memory is the strongest non-coercive return mechanic (VOICE, HOOKS) | PS-CORE-IA-016; §6 "The temporal spine"; PS-P-009 clarification | Priority 3; `PS-MIA-REPLAY-001` Phase 9 | Experience §5 Then and Now |
| T3 | Change over time is meaningful only when source-linked (HOOKS) | PS-CORE-IA-016; PS-CORE-AI-007 | Priority 3 "after confirmed history is mature" | Experience §5 inputs and controls |
| T4 | Season-level intention improves prompt relevance (VOICE) | §7 Connected-room patterns — Focus Theme | Priority 4 | Experience §6 |
| T5 | Members want to keep a meaningful artifact without a trophy case (VOICE) | §7 — Progress Keepsake | Priority 4 | Experience §7 |
| T6 | Absence must be treated as continuation (VOICE) | PS-P-016; §11 "Momentum hooks, not pressure hooks"; PS-CORE-VAL-005 | Priority 3 welcome-back behavior | Experience §8 aligned copy |
| T7 | Weekly narrative beats a score dashboard (VOICE, B26 Slate Replay) | B26 Slate Replay unchanged; PS-CORE-IA-016 | Priority 3 Replay note; Phase 9 | Experience §1 rule 9 |

## 5. Voice and modality

| # | Research finding | Candidate Bible authority | Roadmap phase / package | Experience / Architecture artifact |
|---|---|---|---|---|
| V1 | Voice becomes a signature medium only once it is a usable object (VOICE) | §9 "Expression-first and modality-flexible"; PS-CORE-FR-010 | `PS-VOICE-001` — released and live; no new work authorized | Architecture §2.1 layer 1 |
| V2 | Prosody-based emotional inference is unsafe (VOICE) | §9 rule; rejected-current list | none — rejected for the current program | Experience §1 rule 8 |
| V3 | Voice delight rituals must wait for trust and usability (VOICE) | §9 preserved later candidates | Priority 4 | Experience §9 status ledger |
| V4 | Raw-audio retention is a member-trust decision, not a default (VOICE) | §19 Open decision 11 | **OPEN — unresolved** | Architecture §7 non-assumptions |

## 6. Measurement and safety

| # | Research finding | Candidate Bible authority | Roadmap phase / package | Experience / Architecture artifact |
|---|---|---|---|---|
| M1 | Connective value must be measured without content logging (HOOKS, B26 PS-CORE-NFR-003) | PS-CORE-NFR-009 | Priority 0 taxonomy; every later package | Architecture §6 event taxonomy |
| M2 | Guardrails must catch overload and pressure, not just adoption (VOICE) | §16 guardrail additions | Priority 0 | Architecture §6 allowed dimensions |
| M3 | Comprehension of "how this room relates to the Slate" is the real outcome (HOOKS) | §16 connected-system comprehension measure | Validation scenario 8 | Roadmap Appendix G §4.8 |
| M4 | Preservation of an idea is routinely misread as approval (B26 §19 pattern) | PS-CORE-GOV-008 | Disposition matrix; status ledger | Experience §9; `08_DISPOSITION_MATRIX.md` |

## 7. Coverage check — every candidate requirement is traced

| Requirement | Traced from | Allocated to |
|---|---|---|
| PS-P-015 | S1 | Architecture §3; Experience §2 |
| PS-P-016 | T6 | Experience §1 rule 9; §8 |
| PS-CORE-VAL-005 | T1, T6 | Experience §1 rule 9; Roadmap Appendix G §4.4 |
| PS-CORE-IA-013 | S1 | Architecture §3.1 |
| PS-CORE-IA-014 | S2 | Architecture §3.2 rules 1–7 |
| PS-CORE-IA-015 | S3 | Experience §1 rules 4–5 |
| PS-CORE-IA-016 | T2, T3 | Experience §5 |
| PS-CORE-FR-009 | S6 | Experience §4 |
| PS-CORE-FR-010 | V1 | Architecture §2.1 layer 1 |
| PS-CORE-DATA-007 | C1, C3, C5 | Architecture §4, §5 |
| PS-CORE-AI-007 | T3 | Experience §5 controls; §1 rule 8 |
| PS-CORE-NFR-008 | S3, C3 | Architecture §3.3; Experience §1 rule 10 |
| PS-CORE-NFR-009 | M1, M2 | Architecture §6 |
| PS-CORE-GOV-008 | M4 | `08_DISPOSITION_MATRIX.md`; Experience §9 |

No candidate requirement is unallocated. No artifact section exists without a
requirement, risk, or constraint justifying it — which is the Bible's own
baseline rule for approving a requirements or architecture baseline.

## 8. What this matrix does not claim

- It does not claim any traced package is authorized, assigned, scheduled,
  started, deployed, enabled, or live.
- It does not verify the four handoff sources absent from the repository.
- It does not close any Open decision. V4 and every row referencing an Open
  decision remain unresolved.
