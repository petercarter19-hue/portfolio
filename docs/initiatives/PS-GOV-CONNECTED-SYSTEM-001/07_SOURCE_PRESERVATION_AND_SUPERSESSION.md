# Source preservation and supersession record (PROPOSED)

> **STATUS: PROPOSED.** Nothing in this file has taken effect. Bible v2.6 and
> Roadmap v2.5 remain current. `DOCUMENT_CONTROL.md` was not edited.

## 1. Preservation — nothing was deleted, moved, or rewritten

| Preserved artifact | Path | State after this package |
|---|---|---|
| Bible v2.6 | `docs/governance/PeerSlate_Company_and_Product_Bible_v2.6.docx` | Byte-for-byte unchanged. Still the current controlling Bible. |
| Roadmap v2.5 | `docs/governance/PeerSlate_Product_Strategy_and_Architecture_Roadmap_v2.5.docx` | Byte-for-byte unchanged. Still the current controlling Roadmap. |
| Bible v2.3, v2.4, v2.5 | `docs/governance/` | Unchanged. Already recorded as superseded. |
| Roadmap v2.3, v2.4 | `docs/governance/` | Unchanged. Already recorded as superseded. |
| Bible v1.1–v1.4 | repository root | Unchanged. Already recorded as superseded. |
| Sync Standard v1.1 | `docs/governance/` | Unchanged. Not affected by this package. |
| Owner Visual Integrity Standard | `docs/governance/OWNER_VISUAL_INTEGRITY_STANDARD.md` | Unchanged and fully carried forward into the candidate. |
| Owner Story Composition Standard | `docs/governance/OWNER_STORY_COMPOSITION_STANDARD.md` | Unchanged and fully carried forward into the candidate. |
| `DECISIONS.md` | `docs/governance/DECISIONS.md` | Unchanged. The new entry is staged, not appended. |
| `DOCUMENT_CONTROL.md` | `docs/governance/DOCUMENT_CONTROL.md` | Unchanged. |
| `CURRENT_BASELINE.yaml`, `CURRENT_STATE.md`, `ACTIVE_INITIATIVES.md` | `docs/governance/` | Unchanged. |
| Owner handoff, PDF, and architecture diagram | `docs/initiatives/PS-GOV-CONNECTED-SYSTEM-001/source/` on `work/2026-07-20-next-task-board` | Preserved by that branch. Not duplicated here. See `00_WRITER_ASSIGNMENT_AND_BASE.md`. |

**Candidate v2.7 removes no v2.6 content.** Every section, subsection, table row,
list entry, requirement, appendix, figure, and callout in v2.6 survives in the
candidate. Section numbers 1–20 are unchanged, appendices A–L keep their
letters, and no principle or requirement identifier is reused, renumbered, or
reworded except the single additive clarifying sentence on PS-P-009 recorded in
`01_CANDIDATE_BIBLE_V2_7_SOURCE.md` §2.1.

## 2. Supersession that would take effect **at activation only**

These lines are drafted for `DOCUMENT_CONTROL.md` and are **not yet applied**.

### 2.1 Current controlled set — rows to change

| Record | From | To |
|---|---|---|
| Company and Product Bible | v2.6 | v2.7 |
| Product Strategy and Architecture Roadmap | v2.5 | v2.6 |

### 2.2 Known supersessions — lines to add

- Bible v2.7 supersedes v2.6, v2.5, v2.4, v2.3, and v1.1 through v1.4 for
  current product decisions.
- Roadmap v2.6 supersedes v2.5, v2.4, and v2.3 for current sequencing and
  architecture decisions.
- The connected-system spine, connected-room contract, and return-value engine
  are constitutional. Connective patterns are canonical experience patterns
  inside existing rooms, never top-level destinations.
- Preservation of a connective or retention idea is not implementation
  authorization. Every such idea carries an explicit Locked / Open / Later /
  Tabled / Rejected-current status.

### 2.3 Current controlled set — rows to add, if and only if the standards are established

| Record | Version/status | Purpose |
|---|---|---|
| Experience System — connective patterns | PROPOSED → CURRENT at activation | The six canonical connective patterns, their modes, states, and content voice |
| Architecture and Data Standard — connected system | PROPOSED → CURRENT at activation | Connected-room logical contract, relationship vocabulary, proof-graph boundary, and privacy-safe event taxonomy |

The repository currently has **no** standalone Experience System or Architecture
and Data Standard document; both are named in the Bible's operating-system table
but exist only as per-initiative files. Establishing them as controlled
artifacts is a governance decision for the activation step, not something this
documentation package may perform.

## 3. Unresolved supersession question — must be settled before approval

`PeerSlate_Company_and_Product_Bible_v1.5.1.pages` is **untracked** in the
repository root. It is dated July 17, 2026, presents itself as an implementation
baseline superseding v1.3 and v1.4, and appears in no supersession list in
`DOCUMENT_CONTROL.md`, which stops at v1.4.

It carries at least two positions that collide with current authority:

1. "The Journal is the member profile," while Journal UI is explicitly on hold
   under `PS-JOURNAL-001`.
2. Iris Foundry color direction, which Deep Navy Gold retired under
   `PS-BRAND-NAV-002`.

**Consequence for this package:** the supersession list in §2.2 says v2.7
supersedes "v1.1 through v1.4." If v1.5.1 is in fact a real intermediate
authority, that list is incomplete and v2.7 would supersede an ambiguous set.

**Recommendation:** resolve the v1.5.1 authority question **before** approving
candidate v2.7, so the new Bible supersedes a known set. This is explicitly
outside this package's scope, is tracked separately on the next-task board, and
was not decided here.

## 4. Candidate file locations

Candidates are held **inside the package**, not in `docs/governance/`, so that
no governance directory listing can be mistaken for current authority:

- `candidate/PeerSlate_Company_and_Product_Bible_v2.7_PROPOSED.docx`
- `candidate/PeerSlate_Product_Strategy_and_Architecture_Roadmap_v2.6_PROPOSED.docx`
- `candidate/build_candidates.py` — the deterministic generator that produced
  both files from their unchanged predecessors

Moving the approved candidates into `docs/governance/` under their final names
is an activation step, listed in `10_ACTIVATION_CHECKLIST.md`.
