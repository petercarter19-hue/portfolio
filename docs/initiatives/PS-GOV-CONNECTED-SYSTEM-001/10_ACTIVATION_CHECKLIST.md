# Activation checklist — NOT PERFORMED

> **None of the steps below was executed by this package.** Section 12.12 and
> 12.13 of the source handoff require activation to be a separate, explicit
> change made only after Pete approves the candidate. Bible v2.6 and Roadmap
> v2.5 remain current.

## 0. Preconditions before activation may start

| # | Precondition | State at this package's completion |
|---|---|---|
| P1 | Pete has read the candidate Bible v2.7 and Roadmap v2.6 and approved them | **Not done** |
| P2 | The owner acceptance checklist in Section 14 of the source handoff passes | **Not done** — see §1 below |
| P3 | The `PeerSlate_Company_and_Product_Bible_v1.5.1.pages` authority question is resolved, so v2.7 supersedes a known set | **Unresolved** — outside this package's scope |
| P4 | `work/2026-07-20-next-task-board` is merged, so the owner handoff and diagram live on `main` beside this package | **Not merged** as of base `531013dd8c1a05e2443becd881a226755f27ca14` |
| P5 | This package's own pull request is merged and its pipeline is green | **Not done** — no PR opened |
| P6 | A designated session manager holds a written shared-governance-file reservation, serialized against `PS-CAPTURE-MEDIA-001`, `PS-HOME-INTERVIEW-PARITY-001`, and `PS-HOME-FRONTEND-001` | **Not held** |

Activation must not begin while any precondition is unmet.

## 1. Owner acceptance checklist (Section 14 of the source handoff)

Pete answers each of these against the candidate before approving.

| # | Question | Where to look |
|---|---|---|
| 1 | Does the Bible clearly say PeerSlate needs a stronger trunk, not more branches? | Executive direction paragraph and `GOVERNING DECISION` callout |
| 2 | Does every major page now have a governing connection rule without losing its distinct purpose? | §6 *The connected-room contract*; PS-P-015; `PS-CORE-IA-013` |
| 3 | Are public and owner modes clearly separated? | §6 contract two-payload rule; `HARD BOUNDARY` callout; `PS-CORE-IA-014` |
| 4 | Is the relationship/proof graph treated as canonical placement and references rather than a new truth store? | §12 `NO NEW SYSTEM OF RECORD`; `PS-CORE-DATA-007`; Architecture §5 |
| 5 | Are Resume Backstory, Studio Return Ticket, Then and Now, Focus Themes, Keepsakes, and voice rituals in the correct priority bands? | §7 *Connected-room patterns*; §19; Roadmap Appendix G; `08_DISPOSITION_MATRIX.md` |
| 6 | Are companion/worldbuilding and buddy concepts preserved without being authorized? | §19 Later and Tabled; disposition matrix LT9, LT10, TB2, TB3 |
| 7 | Are hard streaks, guilt, badges, infinite feeds, generic AI rails, and automatic publication explicitly rejected for the current program? | §19 *Rejected for the current program*, sixteen entries |
| 8 | Does the architecture map show source → canonical → relationship → room → action → outcome → return? | Appendix N `THE LOOP` callout, Figure N-1, eight-layer table |
| 9 | Are new requirements measurable and traceable? | §14 twelve requirements; `06_TRACEABILITY_MATRIX.md` coverage check |
| 10 | Does the Roadmap preserve current release truth and package gates? | Roadmap approval note; the six replacements are front-matter only; every phase and package row is untouched |
| 11 | Does the candidate remain non-controlling until approval? | PROPOSED in the version table, status band, approval note, and filename; no pointer file changed |
| 12 | Is the final document professionally rendered and consistent with the existing Bible's visual system? | The candidate inherits v2.6's styles, headers, footers, numbering, theme, and media; new content reuses the source documents' own heading, list, requirement, callout, status-band, and navy-header table patterns |

## 2. Activation steps, in order

Each step is a normal governed change on its own branch with its own review.

1. **Move the approved candidates into `docs/governance/`** under their final
   names, dropping the `_PROPOSED` suffix:
   - `PeerSlate_Company_and_Product_Bible_v2.7.docx`
   - `PeerSlate_Product_Strategy_and_Architecture_Roadmap_v2.6.docx`
   Update their version tables, status bands, and approval notes from `PROPOSED`
   to `CURRENT` / `LOCKED` with the approval date. Leave v2.6 and v2.5 in place
   as historical records.
2. **Update `docs/governance/CURRENT_BASELINE.yaml`:** `governing_documents.bible`
   to version `2.7` and its new path; `governing_documents.roadmap` to version
   `2.6` and its new path; add `PeerSlate_Company_and_Product_Bible_v2.6.docx`
   and `PeerSlate_Product_Strategy_and_Architecture_Roadmap_v2.5.docx` to
   `superseded_documents`; add `PS-GOV-CONNECTED-SYSTEM-001` to
   `completed_packages`; record the activation merge commit and pipeline.
3. **Update `docs/governance/DOCUMENT_CONTROL.md`** using the exact rows and
   lines drafted in `07_SOURCE_PRESERVATION_AND_SUPERSESSION.md` §2.
4. **Update `docs/governance/CURRENT_STATE.md`** with the activation merge SHA,
   pipeline result, and an honest boundaries entry stating that no connective
   pattern is implemented, assigned, or live.
5. **Update `docs/governance/ACTIVE_INITIATIVES.md`** to record
   `PS-GOV-CONNECTED-SYSTEM-001` as complete and the three connective package
   IDs as candidate/unassigned.
6. **Append the Decision Register entry** — the verbatim block in
   `05_DECISION_REGISTER_ENTRY.md` — to the end of
   `docs/governance/DECISIONS.md`.
7. **Update the guardrail suite** `tests/test_governance_pointers.py`:
   `test_baseline_names_current_authority_and_manager` asserts
   `Bible_v2.6` and `Roadmap_v2.5`; both assertions must move to `Bible_v2.7`
   and `Roadmap_v2.6` in the **same** change that updates the baseline, or the
   suite will fail. Add this package's required records to `REQUIRED` if the
   manager wants them guarded.
8. **Decide whether to establish standalone Experience System and Architecture
   and Data Standard documents.** If yes, move package files `03_` and `04_`
   into `docs/governance/`, add them to the `DOCUMENT_CONTROL.md` controlled
   set, and point `CURRENT_BASELINE.yaml` at them. If no, they remain
   package-local and the Bible's operating-system table keeps naming them as
   intended-but-not-yet-established artifacts.
9. **Release** through an Azure pull request with squash merge, confirm the
   pipeline passes for the exact merge commit, and verify that public routes are
   unchanged. This is a documentation release; it must change no runtime
   behavior.

## 3. What activation still does not do

Activation makes v2.7 the controlling Bible. It does **not**:

- enable Owner Home, Photo Capture, Projects, Journal UI, or any gated
  capability;
- authorize, assign, schedule, or start `PS-PUBLIC-CONNECTIVE-001`,
  `PS-CONNECTIVE-COMPONENT-001`, `PS-RETURN-VALUE-001`, or any connective
  pattern;
- change any feature flag, route, schema, deployment, or production setting;
- close any of the eleven Open decisions;
- alter `PS-HOME-INTERVIEW-PARITY-001`, `PS-HOME-FRONTEND-001`, or
  `PS-CAPTURE-MEDIA-001`.

Each connective package still needs its own manager, writer, branch, entry gate,
accepted production-intent visual authority, evidence, Pete plus
designated-manager acceptance, Azure release, and live verification.
