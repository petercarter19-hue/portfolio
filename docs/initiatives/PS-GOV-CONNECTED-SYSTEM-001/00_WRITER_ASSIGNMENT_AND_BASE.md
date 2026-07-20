# PS-GOV-CONNECTED-SYSTEM-001 — Writer assignment, base, and file boundary

> **STATUS: PROPOSED — documentation and governance only.** Nothing in this
> package is controlling authority. Bible v2.6 and Roadmap v2.5 remain current
> until Pete approves the candidate and a separate activation change updates the
> pointer chain.

## Assignment

| Field | Value |
|---|---|
| Package | `PS-GOV-CONNECTED-SYSTEM-001` |
| Work type | Documentation and governance only; zero runtime impact |
| Controlling specification | `source/PeerSlate_Connected_System_and_Hooks_Bible_Update_Handoff_v1.md` (handoff v1.0, July 20, 2026) |
| Writer | Claude Code (sole writer). The source handoff names Codex; Pete reassigned the writer role. Every other instruction in the handoff applies unchanged. |
| Designated session manager | The Claude Code manager session that issued this assignment |
| Branch | `docs/connected-system-return-value-authority` |
| Base | `origin/main` at `531013dd8c1a05e2443becd881a226755f27ca14` |
| Runtime impact | None. No feature flag, route, schema, template, service, migration, pipeline, or production setting is touched. |

### Branch-naming exception

`docs/AI_WORKFLOW.md` normally requires a `work/YYYY-MM-DD-task-name` branch.
Section 12.3 of the source handoff and the owner's assignment both name
`docs/connected-system-return-value-authority` explicitly. That explicit
instruction is the recorded exception. Every other rule in `docs/AI_WORKFLOW.md`
— single writer, squash merge through an Azure pull request, no direct write to
`main` — applies unchanged.

## Source-material location (read this before reviewing the package)

The owner-supplied handoff, its rendered PDF, the architecture diagram, and this
package's `README.md` were staged by a different lane on
`work/2026-07-20-next-task-board` at `34156b3eaa97beda303a5cc1f1b870bb39f97a9d`,
which is pushed to `origin` but **not merged into `main`**.

This branch was created from exact `origin/main`, so it does not contain those
files. That is deliberate:

- Duplicating `README.md` or `source/` here would put the same paths under two
  writers on two unmerged branches.
- Every file this package adds is new and numbered, so the two branches combine
  additively without a content conflict.

**Reviewer consequence:** read the source handoff from
`work/2026-07-20-next-task-board`, or merge that staging branch first. If the
staging branch is abandoned, this package's `source/` references become dangling
and the handoff must be re-staged before activation.

## Files this branch writes

All paths are new. No existing repository file is modified.

| Path | Purpose |
|---|---|
| `00_WRITER_ASSIGNMENT_AND_BASE.md` | This record |
| `01_CANDIDATE_BIBLE_V2_7_SOURCE.md` | Authoritative source text for every candidate Bible v2.7 change |
| `02_CANDIDATE_ROADMAP_V2_6_SOURCE.md` | Candidate Roadmap revision and priority/package crosswalk |
| `03_ARCHITECTURE_AND_DATA_STANDARD_CONNECTED_SYSTEM.md` | Proposed Architecture and Data Standard section: connected-room logical contract |
| `04_EXPERIENCE_SYSTEM_CONNECTIVE_PATTERNS.md` | Proposed Experience System section: the six connective patterns |
| `05_DECISION_REGISTER_ENTRY.md` | Decision Register entry, staged for append at activation |
| `06_TRACEABILITY_MATRIX.md` | Research finding → principle/requirement → phase/package → artifact |
| `07_SOURCE_PRESERVATION_AND_SUPERSESSION.md` | What v2.7 would supersede and what is preserved |
| `08_DISPOSITION_MATRIX.md` | Locked / Open / Later / Tabled / Rejected-current classification |
| `09_CHANGE_REPORT.md` | File-by-file diff summary, rationale, open decisions, deferrals |
| `10_ACTIVATION_CHECKLIST.md` | The separate post-approval activation steps — **not performed** |
| `candidate/PeerSlate_Company_and_Product_Bible_v2.7_PROPOSED.docx` | Rendered candidate Bible |
| `candidate/PeerSlate_Product_Strategy_and_Architecture_Roadmap_v2.6_PROPOSED.docx` | Rendered candidate Roadmap |
| `candidate/build_candidates.py` | Deterministic generator that produced both candidate `.docx` files from their v2.6 / v2.5 predecessors |
| `COMPLETION_REPORT.md` | Owner technical completion report |

## Files this branch deliberately does not write

| Path | Why not |
|---|---|
| `docs/governance/CURRENT_BASELINE.yaml` | Hard exclusion. Bible v2.6 / Roadmap v2.5 stay current until Pete approves. |
| `docs/governance/CURRENT_STATE.md` | Hard exclusion. No production or authority state changed. |
| `docs/governance/ACTIVE_INITIATIVES.md` | Shared governance file reserved by the active ChatGPT Work/Codex manager lane. |
| `docs/governance/DOCUMENT_CONTROL.md` | Same. Supersession is recorded in `07_SOURCE_PRESERVATION_AND_SUPERSESSION.md` for the activation step. |
| `docs/governance/DECISIONS.md` | Append-only shared record. The entry is staged in `05_DECISION_REGISTER_ENTRY.md` and appended at activation. |
| `docs/governance/PeerSlate_Company_and_Product_Bible_v2.6.docx` | Preserved unchanged as historical authority. |
| `docs/governance/PeerSlate_Product_Strategy_and_Architecture_Roadmap_v2.5.docx` | Preserved unchanged as historical authority. |
| `docs/initiatives/PS-GOV-CONNECTED-SYSTEM-001/README.md` | Owned by the unmerged staging branch. |
| Any application code, template, test, migration, pipeline, or configuration file | Runtime impact is not permitted. |

## Shared-governance serialization check

As of base `531013dd8c1a05e2443becd881a226755f27ca14`, `CURRENT_BASELINE.yaml`
lists three active packages under a ChatGPT Work/Codex designated manager:
`PS-CAPTURE-MEDIA-001`, `PS-HOME-INTERVIEW-PARITY-001`, and
`PS-HOME-FRONTEND-001`. This package therefore touches **no** shared governance
file and needs no reservation. Activation, which does touch them, must be
serialized against those lanes.

## Open decisions preserved

The eleven Open decisions in Section 8.2 of the source handoff are carried
forward as `OPEN` in the candidate Bible Section 19, in
`08_DISPOSITION_MATRIX.md`, and in `09_CHANGE_REPORT.md`. None was closed,
narrowed, or answered by this package.
