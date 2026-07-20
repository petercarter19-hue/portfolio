# Change report — PS-GOV-CONNECTED-SYSTEM-001

> Documentation and governance only. Zero runtime impact. Nothing in this
> package is controlling authority.

**Branch:** `docs/connected-system-return-value-authority`
**Base:** `origin/main` at `531013dd8c1a05e2443becd881a226755f27ca14`
**Writer:** Claude Code (reassigned from Codex by Pete)

---

## 1. File-by-file summary

Every path is **new**. No existing repository file is modified, moved, renamed,
or deleted.

| Path | Kind | What it contains |
|---|---|---|
| `docs/initiatives/PS-GOV-CONNECTED-SYSTEM-001/00_WRITER_ASSIGNMENT_AND_BASE.md` | new | Writer/manager/branch/base record, branch-naming exception, source-material location, complete written/not-written file boundary, shared-governance serialization check |
| `…/01_CANDIDATE_BIBLE_V2_7_SOURCE.md` | new | Authoritative source text for every candidate Bible v2.7 change, anchored to its insertion point |
| `…/02_CANDIDATE_ROADMAP_V2_6_SOURCE.md` | new | Authoritative source text for every candidate Roadmap v2.6 change, plus the priority and package crosswalk |
| `…/03_ARCHITECTURE_AND_DATA_STANDARD_CONNECTED_SYSTEM.md` | new | Proposed Architecture and Data Standard section: eight-layer map, `ResolvedRoomContext` logical contract, ten rules, seventeen behavior states, relationship vocabulary, proof-graph boundary, privacy-safe event taxonomy, explicit non-assumptions |
| `…/04_EXPERIENCE_SYSTEM_CONNECTIVE_PATTERNS.md` | new | Proposed Experience System section: ten shared rules, six patterns with elements/placement/states/rules, connective content voice, all-`no` status ledger |
| `…/05_DECISION_REGISTER_ENTRY.md` | new | Verbatim `DECISIONS.md` block staged for append at activation, plus context, five alternatives considered, six risks with mitigations, supersession language, and the unresolved v1.5.1 question |
| `…/06_TRACEABILITY_MATRIX.md` | new | Research finding → principle/requirement → phase/package → artifact crosswalk across six themes, plus a coverage check proving no candidate requirement is unallocated |
| `…/07_SOURCE_PRESERVATION_AND_SUPERSESSION.md` | new | Preservation table, the exact `DOCUMENT_CONTROL.md` lines that would change **at activation only**, and the unresolved v1.5.1 supersession question |
| `…/08_DISPOSITION_MATRIX.md` | new | Complete Locked (12) / Open (11) / Later (10) / Tabled (9) / Rejected-current (16) classification |
| `…/09_CHANGE_REPORT.md` | new | This file |
| `…/10_ACTIVATION_CHECKLIST.md` | new | The separate post-approval activation steps — explicitly **not performed** |
| `…/COMPLETION_REPORT.md` | new | Owner technical completion report, sections A–I |
| `…/candidate/build_candidates.py` | new | Deterministic generator with built-in structural verification |
| `…/candidate/PeerSlate_Company_and_Product_Bible_v2.7_PROPOSED.docx` | new | Rendered candidate Bible |
| `…/candidate/PeerSlate_Product_Strategy_and_Architecture_Roadmap_v2.6_PROPOSED.docx` | new | Rendered candidate Roadmap |

**Unchanged and verified unchanged:** `docs/governance/PeerSlate_Company_and_Product_Bible_v2.6.docx`,
`docs/governance/PeerSlate_Product_Strategy_and_Architecture_Roadmap_v2.5.docx`,
`CURRENT_BASELINE.yaml`, `CURRENT_STATE.md`, `ACTIVE_INITIATIVES.md`,
`DOCUMENT_CONTROL.md`, `DECISIONS.md`, `START_HERE.md`, `AGENTS.md`,
`CLAUDE.md`, `docs/AI_WORKFLOW.md`, and every application, template, test,
migration, and pipeline file.

---

## 2. Exact sections changed in candidate Bible v2.7

The candidate is v2.6 with the changes below applied. **Nothing was removed.**
Only eight lines of v2.6 text were replaced; everything else is additive.
Sections 1–20 keep their numbers and appendices A–L keep their letters.

### 2.1 The eight replacements

| # | v2.6 text | v2.7 text | Rationale |
|---|---|---|---|
| 1 | VERSION `v2.6 - Projects System Authority` | `v2.7 - Connected System and Return-Value Authority (PROPOSED)` | Candidate identity |
| 2 | DATE `July 19, 2026` | `July 20, 2026` | Candidate date |
| 3 | STATUS `CURRENT - OWNER-APPROVED …` | `PROPOSED - CANDIDATE AWAITING OWNER APPROVAL; v2.6 REMAINS CURRENT` | The candidate must not read as current |
| 4 | SOURCE SYNTHESIS line | v2.6 + July 20 connected-system decision | Accurate basis |
| 5 | Document-control authority band, labelled `LOCKED` | Same band relabelled `PROPOSED`, stating v2.6 remains controlling | Prevents a reader from treating the candidate as authority |
| 6 | Approval note | Candidate approval note preserving the whole v2.6 constitution and naming the one governing decision | Accurate status and scope |
| 7 | Table-of-contents note | Same note plus a sentence naming the new headings and the refresh step | Honest about the stale cached field |
| 8 | Document map appendix line | Adds "connected-system" to the appendix description | Discoverability |

Plus one **additive** clarifying sentence appended to the existing PS-P-009
decision rule, exactly as the source handoff requires. PS-P-009 keeps its ID,
name, and original wording.

### 2.2 The additions

| Bible location | Addition |
|---|---|
| Executive direction | Governing paragraph on the stronger visible trunk, plus a `GOVERNING DECISION` callout: "Every page should feel like a different use of the same life." |
| §3 Governing product principles | PS-P-015 *Focused rooms, visible spine*; PS-P-016 *Momentum without pressure* |
| §4 Product boundaries | 2 additions to "PeerSlate is"; 3 additions to "PeerSlate is not" |
| §5 One connected Slate | New subsections *The connected-system spine* and *Relationship before promotion* |
| §6 Experience model and IA | New locked subsection *The connected-room contract* (status band, five questions, two mode payloads, `HARD BOUNDARY` callout); *Focused but not orphaned*; *The temporal spine* |
| §7 Signature experiences | New subsections *Connected-room patterns* (six-pattern table + not-live note) and *The return-value engine* |
| §9 AI, sources, member intelligence | New subsection *Expression-first and modality-flexible* + ten preserved voice-delight candidates |
| §11 Design and quiet delight | New subsection *Momentum hooks, not pressure hooks*; six new quiet-delight rows |
| §12 Technical direction | Two paragraphs under *Architecture posture*; `NO NEW SYSTEM OF RECORD` callout |
| §14 Mandatory requirements | PS-CORE-VAL-005; IA-013 to IA-016; FR-009, FR-010; DATA-007; AI-007; NFR-008, NFR-009; GOV-008 — twelve requirements |
| §16 Metrics | Nine new core measures; five new guardrails |
| §19 Decisions | 12 Locked, 11 Open, 10 Later, 8 Tabled entries; new subsection *Rejected for the current program* with 16 entries |
| New Appendix M | Connected-system and return-value covenant |
| New Appendix N | Connected-system architecture map, embedded diagram, eight-layer table, cross-cutting controls |

### 2.3 Identifier collision check

Every new identifier was checked against v2.6 before use.

| Family | v2.6 highest | v2.7 adds | Collision |
|---|---|---|---|
| PS-P | 014 | 015, 016 | none |
| PS-CORE-VAL | 004 | 005 | none |
| PS-CORE-IA | 012 | 013–016 | none |
| PS-CORE-FR | 008 | 009, 010 | none |
| PS-CORE-DATA | 006 | 007 | none |
| PS-CORE-AI | 006 | 007 | none |
| PS-CORE-NFR | 007 | 008, 009 | none |
| PS-CORE-GOV | 007 in §14.9; 010–014 in Appendix I | 008 | none (008 and 009 were unused) |
| Appendix letters | L | M, N | none |

---

## 3. Exact sections changed in candidate Roadmap v2.6

Six replacements, three additive blocks, and one new appendix. **No phase
status, package status, pipeline number, merge SHA, release record, or
production claim changed.**

| # | Change |
|---|---|
| 1 | VERSION → `v2.6 - Connected-System Sequencing (PROPOSED)` |
| 2 | DATE → July 20, 2026 |
| 3 | STATUS → `PROPOSED - CANDIDATE AWAITING OWNER APPROVAL; v2.5 REMAINS CURRENT` |
| 4 | SOURCE SYNTHESIS → v2.5 + candidate Bible v2.7 + July 20 decision |
| 5 | Roadmap authority band relabelled `LOCKED` → `PROPOSED`, text states v2.5 remains current |
| 6 | Approval note → candidate note stating every v2.5 status is preserved exactly |
| 7 | §18 Work-package register: three **CANDIDATE, unassigned** rows — `PS-PUBLIC-CONNECTIVE-001`, `PS-CONNECTIVE-COMPONENT-001`, `PS-RETURN-VALUE-001` — plus a note that register presence is not authorization |
| 8 | §20 "What not to do next": four new entries (no generic rails; no streak meter; no connective pattern before its entry gate; no Then and Now before mature history) |
| 9 | New **Appendix G — Connected-system and return-value direction amendment**: Priority 0 through Priority 5, entry gates, the Priority-2 acceptance-outcome table, verification expectations, ten validation scenarios, and current control |

---

## 4. Open decisions preserved — none closed

All eleven Open decisions from Section 8.2 of the source handoff are carried
forward as `OPEN` in candidate Bible §19, in `08_DISPOSITION_MATRIX.md`, and
here. This package answered, narrowed, or implied an answer to **none** of them.

1. Exact visual form and canonical name of the Slate Spine.
2. Whether the first public pilot is a new package or an amendment to active
   Resume/Studio packages.
3. Which three to five Resume achievements receive Backstory Drawers.
4. Whether public Studio support is curated configuration or projection-backed
   after canonical services mature.
5. Exact owner-mode Return Ticket actions and storage.
6. Exact cadence and user controls for Replay and resurfacing.
7. Whether Focus Themes are fixed, member-authored, AI-suggested, or hybrid.
8. Whether Progress Keepsakes live inside Replay, My Slate, Story, or a private
   collection view.
9. Whether a soft consistency visualization is useful without becoming a streak.
10. Notification policy, channels, timing, and opt-in defaults.
11. Raw-audio retention and voice-processing disclosures.

---

## 5. Hard exclusions — compliance statement

| Section 3 exclusion | Compliance |
|---|---|
| No feature flag, route, schema, deployment, or production setting changed | No application, template, migration, pipeline, or configuration file is in the diff |
| Owner Home, Photo Capture, Projects, and gated capability not enabled | Untouched; the candidates restate that Owner Home is default-off, Photo is flag-off, Journal is on hold, Projects are planned |
| No planned, browser-local, flag-off, or unassigned capability described as live | Every connective pattern carries an explicit not-live statement; Architecture §2.1 states current per-layer reality at the exact base SHA; the Experience System carries an all-`no` status ledger |
| No new top-level destination | Patterns are explicitly "canonical experience patterns, not top-level destinations"; a global Insights/Engagement destination is on the rejected list |
| No second source of truth | `PS-CORE-DATA-007` forbids copied facts; Architecture §5 forbids a new system of record; room-specific truth stores are on the rejected list |
| No assumed table, provider, API, notification system, or AI model | Architecture §7 is an explicit non-assumption list; notification policy is preserved as Open decision 10 |
| No addiction, guilt, loss, or public-performance language | PS-P-016, `PS-CORE-VAL-005`, and *Momentum hooks, not pressure hooks*; 16 rejected mechanics |
| Bible not converted into an implementation specification | Detailed contracts sit in package files 03 and 04; the Bible carries the covenant and the high-level map only |
| No controlling pointer updated to claim v2.7 is current | `CURRENT_BASELINE.yaml`, `CURRENT_STATE.md`, `ACTIVE_INITIATIVES.md`, `DOCUMENT_CONTROL.md`, and `DECISIONS.md` are untouched; both candidates are labelled PROPOSED and live inside the package, not in `docs/governance/` |
| No Open decision silently closed | All eleven preserved, listed in three places |
| No pull request, merge, or push to `main` | Branch pushed only; no PR opened |

---

## 6. Intentionally deferred

| # | Deferred item | Why | Who resolves it |
|---|---|---|---|
| D1 | Rendered PDF review artifact | No PDF renderer is available in this environment (no `pandoc`, no Word, no LibreOffice, no `python-docx`). The `.docx` candidates are complete and open in Word. | Pete or a machine with Word/LibreOffice, if the repository standard requires a PDF |
| D2 | Refreshed table-of-contents page numbers | Page numbers cannot be computed without a layout engine. Both TOC fields are marked **dirty**, so Word rebuilds entries and page numbers on open; the cached entries shipped in the files are stale by design and a note in each document says so. | Word, automatically on open |
| D3 | Establishing standalone Experience System and Architecture and Data Standard documents | Neither exists in the repository yet. Creating new controlled Layer-2 artifacts is a governance decision, and `DOCUMENT_CONTROL.md` is a shared file held by another lane. | Activation step, serialized against the active lanes |
| D4 | Appending the Decision Register entry | `DECISIONS.md` is a shared append-only governance record; three active packages sit under a different designated manager. | Activation step |
| D5 | Resolving the `PeerSlate_Company_and_Product_Bible_v1.5.1.pages` authority question | Explicitly outside this package's scope, but it must be settled **before** v2.7 is approved so the supersession list names a known set. | Pete, tracked separately |
| D6 | Independent verification of four handoff sources | The Product and Architecture Brief, Technical Architecture and Release State, Hooks and Connected-Site Research Report, and Deep Research Report on Voice-First Hooks are named in the handoff but are **not in the repository**. The traceability matrix traces the findings as the handoff states them and says so. | Pete, if those sources should be added to the repository |
| D7 | Moving the approved candidates into `docs/governance/` | An activation step, deliberately not performed while they are candidates. | Activation step |

---

## 7. Known dependency and risk

The owner handoff, its PDF, the architecture diagram, and this package's
`README.md` live on `work/2026-07-20-next-task-board` at
`34156b3eaa97beda303a5cc1f1b870bb39f97a9d`, which is pushed to `origin` but not
merged into `main`. This branch was created from exact `origin/main` and does not
duplicate them, so the two branches combine additively.

**Consequence:** if the staging branch is abandoned, this package's references to
`source/…` become dangling and the handoff must be re-staged before activation.
The diagram embedded in Bible Appendix N was read from that branch at build time;
the image bytes now live inside the candidate `.docx`, so the rendered candidate
is self-contained regardless.

---

## 8. Verification performed

See `COMPLETION_REPORT.md` section F for the exact commands and results.
