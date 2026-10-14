# Guide server B1: acceptance and execution record

## B1 round-one correction plan (before correction code)

Claude's full independent review is preserved at coordination commit `16aaf54`, `Shared/handoffs/2026-10-13_claude-pc_to-codex-pc_REVIEW_PS-GUIDE-SERVER-001_B1.md` (246 lines, reviewer `session:9fb18da7-d312-4e90-a956-7f3718e5969f`). Candidate `e05f1d8afd0c1e7eaa8b5a75a7a85909df758a1f` is **FAIL**, not accepted or mergeable. The record below supplements rather than replaces any finding, test limitation or acceptance criterion in that note. No prior review proof is promoted to the corrected candidate.

| Finding | Planned disposition / owner |
|---|---|
| M1 publication version encodings | Fix in B1: carry canonical integer content version/access revision through the draft presentation, compare the publication's own version basis and reproduce fresh publish/edit on the real 8444-shaped HTTP fixture. |
| D1 suggestions mistaken for unpublished changes | Fix in B1 per Claude manager ruling: derive changes only from the saved draft versus current publication; waiting/declined proposals do not cause changes waiting. |
| D2 saved/hidden state overwritten | Fix in B1 at the projection choke point; keep base state, expose separate update-waiting flag/count, route rejected saved targets to legacy outcomes; saved/hidden × pending/rejected × card/child table. |
| D3 Projects/story/contact classification | Fix in B1: Independent Project maps to Projects; Story/Contact have explicit non-tab classification outside note counts; saved knowledge retains its stored section. |
| m1 waiting children omitted | Fix in B1 with explicit per-state child counts, separate from top-level cards. |
| m2 identity collision on tied creation times | Fix in B1: reserve all persisted refs and aliases before minting any new ref. |
| m3 pre-B1 identity changes at first save | Fix in B1: use the same deterministic binder on a detached read and commit; GET never persists. |
| m4 bad Guide annotation blocks privacy deletion | Fix in B1 narrowly on purge commits: tolerate/repair invalid Guide identity annotations so source deletion cannot be blocked; preserve facts and existing privacy/source authorization. |
| m5 token omits publication | Fix in B1: finalize the owner-bound token after publication state is filled at the route. |
| m6 per-item published flag/change count absent | Explicit carry-forward to **B2, this same writer/package**, before C2 hide/show/privacy counts; do not make C1/C2 promises using absent fields. Record the extension before B2 code/freeze. |
| m7 endpoint admission order/misleading hard_cap | Fix in B1: validate endpoint through the existing provider constructor before port admission, and distinguish configured cap from purpose ceiling. |
| m8 acceptance mapping/contributing source | Add contributing-source removal test in B1. Unequal numbers/qualifiers and different-role matching belong to **B3, this same writer/package**, with focused pre-code criteria and exact-SHA review. B1's non-merging projection proves preservation only, not matching quality or original V001 cause. |

Observe the focused new reproductions RED, correct within existing claimed surfaces, run affected checks and necessary retained-browser/load proof, freeze/push a new exact SHA and request Claude's delta review. No merge, factory qualification, private cutover, paid call or release is authorized by the FAIL or this plan.

**Goal:** deliver the upload/organize server foundation and a reviewed B1/C1 contract for the approved R6q Guide, with extraction quality before screen and conversation work.

**Authority:** Pete's October 12 assignment and direct clarification start packages 1–3 now; package 4 follows the API freeze. Writer `session:01a132fe-1f81-77f3-8821-d53d157ca025`; independent Protected reviewer Claude PC `local_4fefa9f6`. Activation PR 1356 merged at `b9d8a53ef5f1560817b43e53e5d4c1814ce64b3f`. Repository work may proceed through accepted merge; production release, schema application, resume-page packages 5–7/9 and Cairn 11 remain held.

**Spec:** build plan v2 and complete `DESIGN_RATIONALE_FOR_BUILDERS.md`, including section 6, read before any freeze; `ARCHITECTURE.md`, `STATE_MAP.md`, `WORDING.md`, `CALL_PATH_TRACE.md` and `EVALUATION_CONTRACT.md` are directly affected references. Guide target is approved R6q, manifest SHA256 `c8eb2aaba6ba3188485bfb8d90259443e007cd7a45fa3dbd01bab773dae91934`, 392 files, 112 screens, 42 journeys/140 steps. Reuse accepted design proof and recheck changed bytes only.

**Architecture:** project one working set from the existing intake snapshot and private resume draft. Keep saved record keys, mint stable pending item references, retain source bindings and truthful receipts; reuse the current document reader and MyDataExtractionAdapter. Fixed named model variants come from package 2 and one provisional Guide switch point feeds the existing server composition. No second extractor/store, global model switch, SQL migration, production flag change or edits to `app.py`.

**Tech stack:** existing Flask route modules, Python services and unittest fake-provider fixtures; current repository adapters and source/proposal/draft records.

## Global constraints and resolved choices

- AI proposes; people decide. Manual values win, source evidence stays immutable, accepted draft and published projection remain separate.
- Identity comes from the server; owner/ref/revision checks precede protected retrieval and mutation.
- Rationale section 6 wins over its superseded source lines: pre-checked second-file checklist; one section order **Impact Statement, Skills, Experience, Projects, Education, Certifications, Awards**; certifications separate; no displayed answer counter (server cap unchanged); Impact Statement 70 words; no universal Guide reply word cap.
- Spoken confident edits follow the recorded PQ1 default. A **Move to… button always stages until saved**. B3/C3 must implement F1's revision-checked cross-type conversion, evidence/link preservation, destination essentials, replay/confirm-once and stale Undo cases; F2 keyboard semantics belong to C3.
- Replies after operations are composed from what actually applied. No streamed model prose that could claim an unapplied change. No false counts, percentages, milestones or saves.
- Skipped/unplaced notes preserve their source and status across reload. Skip/source removal never deletes accepted content.
- All initial tests use fake providers and make no paid model/Speech calls. Real-call windows and ledgers remain separately coordinated with bakeoff owner `01a13167-4798-75c0-93e0-8e2da6b7f7bb` before use. The provisional product model's medium effort differs from this build chat's xhigh effort.
- Panel round N merges only after server round N. Package 1 owns the shared server test fixture; package 4 owns the shared browser runner/tests. This package adds focused modules and requests registration without changing their surfaces.
- Preserve public-trust ownership, including `app.py`, shared header/footer/fonts, media chooser, database service, safe return, legacy Pete content and the evidence-companion JS/partial. No resume-page or Ask-card redesign.

## Review focus

1. Foreign owner refs, stale revisions and read failures must not expose private data or be rendered as an empty/new member.
2. Multiple uploads and a later match must preserve stable item identity and all source evidence without duplicating accepted or pending content.
3. Notes with unequal numbers/qualifiers or different roles must remain distinct; extraction must never invent an attribution, number or required value.
4. Incumbent no-variant construction, requests and envelopes stay unchanged; mismatched named variant/settings/result identities fail before provider work or acceptance.
5. A source removal or retry must preserve manual/accepted content and return a truthful stored receipt, with no second extractor or store.

## B1 execution plan

Use native execution in this owning chat, with Claude's exact-SHA review. Each task writes focused failing tests first, observes the expected failure, implements, validates and commits.

- [ ] **Read and pin interfaces before freeze.** Inspect the current repository/draft/source/proposal shapes and affected route envelopes against the rationale. Document B1/C1 request/response/status/revision semantics in this fixed record with exact source/contract version. Route any unlisted material conflict to Claude through `Shared/handoffs`; continue disjoint work. Freeze only after this inspection and executable tests, not from a copied prototype.
- [ ] **Working-set projection.** Extend `services/resume_guide_service.py` and the existing intake integration; add `services/resume_guide_contract.py` and `tests/test_resume_guide_service.py`. Compute sections/items/children/counts from saved items plus live proposals/outcomes; saved refs remain record keys and pending refs remain stable through revisions. Resolve all refs against the owner. Test mixed saved/pending, two uploads, replay/reload, children, hidden/unplaced notes, foreign owner and unavailable reads. No save on read/navigation.
- [ ] **Extraction/model integration.** `services/resume_intake_runtime.py`, `services/my_data_extraction_adapter.py`, `services/resume_guide_model.py`, existing extraction tests and `tests/test_resume_guide_model.py`. Consume the fixed named variant records after package 2 is accepted; broaden only its approved matrix and compose one adapter per selected variant. Keep absent-variant behavior identical. Replay a fictional equivalent of the known PDF failure and record the exact failing stage; retain normalize-date and empty-candidate one-reask behavior. Test unsupported efforts/audiences/identities and fake-provider extracted source/placement fidelity.
- [ ] **B1 route and receipt proof.** `resume_intake_routes.py` and focused route tests expose the frozen working set and actual organize stage/results on the existing foundations. Read errors stay unavailable, owner fields are refused, counts are derived and receipts identify actual server revisions. Test real Flask HTTP with fake providers, source-bound notes and complete save/reload. Browser work remains with package 4.
- [ ] **B1 exact candidate and review.** Freeze/push, self-review the owned diff, publish branch/SHA/change/tests/acceptance through `Shared/handoffs`, receive Claude's exact-SHA review, correct findings and add only the fixed receipt/evidence tail. Use normal current-target CI and merge preflight. Record accepted source separately from installed and real-model evidence. A later B round starts with its own committed focused baseline/criteria before code; this record remains the one package evidence home.

## Later rounds (not B1 completion claims)

B2 adds shared essentials, review decisions, hidden/show, types/order and evidence/highlight references. B3 adds typed exactly-once turns, matching pending items, names, held turns, attachment/contribution lifecycle, manual precedence and F1's six staged-conversion cases. B4 adds live-words tickets/usage/receipt integration. Each round requires fresh exact-SHA Claude review and precedes its matching C round. The UI implements the approved R6q state/wording and screenshot acceptance, including F2; this package creates no new visual direction.

## B1 acceptance plan (committed before product code)

The focused pre-change source blobs match accepted main; run initially from the unchanged application in the C14 worktree. The first load lacked the CI placeholder environment; the same command passed after setting only process-local `ANTHROPIC_API_KEY=test-key-for-ci-only`, as CI does. No real credential or provider call was used. Record both results rather than rewriting history.

```json
{
  "schema_version": 1,
  "package": "PS-GUIDE-SERVER-001",
  "plan_sha": "a9a26c46ee4e73053faa5d26e1111638474fab45",
  "baseline": [
    {
      "command": "X:\\PeerSlate\\runtimes\\development\\Scripts\\python.exe -B -m unittest tests.test_resume_intake_service tests.test_resume_intake_runtime tests.test_resume_intake_routes -q",
      "exit_code": 1,
      "observation": "App import refused missing ANTHROPIC_API_KEY before tests; no provider call or product change."
    },
    {
      "command": "X:\\PeerSlate\\runtimes\\development\\Scripts\\python.exe -B -m unittest tests.test_resume_intake_service tests.test_resume_intake_runtime tests.test_resume_intake_routes -q",
      "exit_code": 0,
      "observation": "162 tests PASS in 7.747 seconds with process-local CI placeholder key and fake providers; no product code changed."
    }
  ],
  "criteria": [
    {
      "id": "b1_contract",
      "expected": "The B1/C1 API is pinned after reading the full current rationale and current source; owner/ref/revision/status/receipt semantics are explicit and executable, with no unlisted material conflict guessed.",
      "verification": "Fixed contract record, focused request/response tests and exact-SHA review."
    },
    {
      "id": "b1_working_set",
      "expected": "One read-only server projection combines saved, pending/revised and hidden/unplaced outcomes into the approved section tree and derived counts; no duplicate store, implicit save or owner leakage.",
      "verification": "Working-set unit tests and owner-isolated real Flask HTTP reads."
    },
    {
      "id": "b1_stable_refs",
      "expected": "Saved refs remain record keys; pending refs persist across revision, second upload, matching and reload; evidence accumulates on the same item and parent/child links remain owner-bound.",
      "verification": "Multiple-source/revision/reload tests with exact item/evidence assertions."
    },
    {
      "id": "b1_extraction_quality",
      "expected": "The known organize failure is replayed with a fictional equivalent and its stage recorded; source/date/number/qualifier attribution is preserved, manual/accepted content survives, unequal notes are not merged and skipped/unplaced status survives reload.",
      "verification": "Focused fake-provider extraction and notes cases, existing date and one-reask regressions; real-model quality remains separately labeled until evaluated."
    },
    {
      "id": "b1_model_composition",
      "expected": "The existing extraction and turn providers consume only approved fixed variants behind one provisional switch point; no variant preserves incumbent requests/envelopes, and mismatched settings/identity/audience/effort fail before paid work.",
      "verification": "Negative contract/adapter/composition tests with fake transport and byte comparisons; package 2 accepted dependency."
    },
    {
      "id": "b1_truthful_state",
      "expected": "Read failures remain unavailable; counts and organize progress derive from actual server work; replies and saved labels require their real receipt/revision, with no invented percentage or lost source.",
      "verification": "HTTP fault/receipt/reload tests and source/state assertions."
    },
    {
      "id": "b1_regression_review",
      "expected": "Affected server regressions pass, no held/shared surfaces change, and Claude independently passes the exact pushed B1 candidate before accepted merge.",
      "verification": "Focused suite results, diff/surface check, exact-SHA receipt and ordinary current-target Azure CI."
    }
  ],
  "candidate_sha": "b0133adef05dcb9af5e479729a48d94bb380ded4",
  "checks": [
    {
      "criterion_id": "b1_contract",
      "result": "pass",
      "kind": "automated",
      "candidate_sha": "b0133adef05dcb9af5e479729a48d94bb380ded4",
      "source_ref": "X:/PeerSlate/coordination/codex-pc-mvp1-build/Shared/handoffs/2026-10-13_claude-pc_to-codex-pc_REVIEW_PS-GUIDE-SERVER-001_B1_D4_recheck.md:4",
      "observed": "Independent exact b0133ade PASS accepts B1 together with all a1077956 delta dispositions; runtime byte identity independently verified. Frozen owner/ref/revision/receipt contract and its executable HTTP/schema tests stand. Uncovered privacy/first-arrival questions received actual manager rulings; auto-open is explicitly B2-0/C2, not a guessed B1 field."
    },
    {
      "criterion_id": "b1_working_set",
      "result": "pass",
      "kind": "automated",
      "candidate_sha": "b0133adef05dcb9af5e479729a48d94bb380ded4",
      "source_ref": "X:/PeerSlate/coordination/codex-pc-mvp1-build/Shared/handoffs/2026-10-13_claude-pc_to-codex-pc_REVIEW_PS-GUIDE-SERVER-001_B1_D4_recheck.md:4",
      "observed": "Independent HTTP RED/GREEN reproduced the exact old missing-parent fixture failure and candidate one-card/one-child/no-unplaced result; all per-state counts and owner-private no-store behavior checked. Existing saved/pending/hidden/unplaced and authorization suites plus current97 focused checks pass; GET projection remains stateless with no duplicate store or implicit save."
    },
    {
      "criterion_id": "b1_stable_refs",
      "result": "pass",
      "kind": "automated",
      "candidate_sha": "b0133adef05dcb9af5e479729a48d94bb380ded4",
      "source_ref": "X:/PeerSlate/coordination/codex-pc-mvp1-build/Shared/handoffs/2026-10-13_claude-pc_to-codex-pc_REVIEW_PS-GUIDE-SERVER-001_B1_D4_recheck.md:4",
      "observed": "Prior independent delta accepted saved UUID keys, deterministic pending refs/revisions, alias reservation and multi-source/evidence/reload preservation. All runtime bytes are identical at b0133ade; new actual HTTP verifies canonical parent/ref/literal fidelity through both Guide and draft APIs. No relationship is minted by reading."
    },
    {
      "criterion_id": "b1_extraction_quality",
      "result": "pass",
      "kind": "automated",
      "candidate_sha": "b0133adef05dcb9af5e479729a48d94bb380ded4",
      "source_ref": "X:/PeerSlate/coordination/codex-pc-mvp1-build/Shared/handoffs/2026-10-13_claude-pc_to-codex-pc_REVIEW_PS-GUIDE-SERVER-001_B1_D4_recheck.md:4",
      "observed": "Prior accepted source/proxy replay proves real PDF reading, literal statements/dates/number/qualifier preservation and a fake provider failure localized after the read, with manual/accepted source preservation. B1 does not merge unequal notes; genuine matching-number/qualifier/different-role cases remain B3 under the accepted disposition. Original V001 provider cause and live quality are not claimed."
    },
    {
      "criterion_id": "b1_model_composition",
      "result": "pass",
      "kind": "automated",
      "candidate_sha": "b0133adef05dcb9af5e479729a48d94bb380ded4",
      "source_ref": "X:/PeerSlate/coordination/codex-pc-mvp1-build/Shared/handoffs/2026-10-13_claude-pc_to-codex-pc_REVIEW_PS-GUIDE-SERVER-001_B1_D4_recheck.md:4",
      "observed": "Accepted package2 immutable variants and prior independent a1077956 constructor/binding/envelope/endpoint/purpose-ceiling corrections remain byte-identical. Fake composition/negative and incumbent-byte tests passed; named modes require the admitted ongoing port and reject mismatches before reserve/token/HTTP. Provisional medium is not permanent product adoption."
    },
    {
      "criterion_id": "b1_truthful_state",
      "result": "pass",
      "kind": "automated",
      "candidate_sha": "b0133adef05dcb9af5e479729a48d94bb380ded4",
      "source_ref": "X:/PeerSlate/coordination/codex-pc-mvp1-build/Shared/handoffs/2026-10-13_claude-pc_to-codex-pc_REVIEW_PS-GUIDE-SERVER-001_B1_D4_recheck.md:4",
      "observed": "Accepted read-outage, page-versus-text-page, source/organization/receipt and numeric-version-versus-opaque-token checks remain unchanged. Standard HTTP publication probe and real saved edit pass; route token is finalized after publication truth. Missing authority stays unknown, pending AI does not imply unpublished change, and access-revision comparison absent from owner_preview is not claimed as exercised."
    },
    {
      "criterion_id": "b1_regression_review",
      "result": "pass",
      "kind": "automated",
      "candidate_sha": "b0133adef05dcb9af5e479729a48d94bb380ded4",
      "source_ref": "X:/PeerSlate/coordination/codex-pc-mvp1-build/Shared/handoffs/2026-10-13_claude-pc_to-codex-pc_REVIEW_PS-GUIDE-SERVER-001_B1_D4_recheck.md:4",
      "observed": "Claude independently PASSed exact b0133ade, no new required finding; all earlier dispositions stand. Writer40 focused and152 normal plus2x152 concurrent browser checks pass; reviewer97 focused passes. No runtime delta since a1077956 or held/shared write; native accepted-main imports are explicit. Normal current-target Azure PR CI remains an external required merge gate and is not claimed complete here."
    }
  ]
}
```

## Current evidence and limitations

- B1 acceptance plan only; API is **not yet frozen**, server implementation/review/merge and installed proof remain pending. Package 4 is not activated.
- Jev status `bcec5601-e522-4fe7-8dd9-6a8d7f63efcc` is unavailable (`ongoing_paused_transport_failure`). Investigation, regression and review-focus checkpoints continue with mandatory source/negative checks and ordinary judgment; no retry, evaluate call or alternative connection.
- The 42 design journeys and approved images are accepted reference evidence. They do not prove this server candidate, real extraction quality, installed behavior or Pete's screenshot OK.

## B1 implementation checkpoints

- The first working-set tests were observed RED before implementation. One stateless projection reads the existing owner intake snapshot and draft view, returns all uploads in the approved section order, keeps saved record keys and persisted pending UUID5 identities/revisions, and exposes an explicit pending-to-saved alias. Direct service fixtures demonstrated nesting when the parent field was supplied. That original checkpoint did **not** establish actual8444 catalog-to-draft-to-HTTP nesting: D4 subsequently identified a separate fixture read-through dropping `parent_key`. The accepted fixture correction and real HTTP proof below close that gap. This read creates no relationship or canonical record.
- Identity annotations are written only at the existing in-memory owner commit, never by a GET. Existing receipts and canonical source values remain separate. Source removal cannot resurrect an unavailable evidence quote or remove the accepted record. Partial manual draft values merge with untouched accepted fields; hidden-only sections do not gain visible tabs. `publication_state` is explicitly `unknown` until the authoritative publication seam is wired, never inferred from sharing flags.
- New `GET /api/resume-intake/me/guide/working-set` uses the existing feature/identity/private-cache boundary and the read rate-limit map; no client query selector is accepted. A read/backend failure returns `load_state: unavailable` with no invented empty counts. An adapter lacking the existing conversation/identity capability remains unavailable; this is private-foundation proof, not SQL engine or production enablement.
- Focused working-set/service/HTTP proof PASS **16 tests**. Affected Guide/intake/proposal/route/draft/conversation/coverage regressions PASS **343 tests in 9.158 seconds**, all fake providers. The first partial-manual-value and hidden-tab tests exposed dropped untouched fields and an over-visible tab; their fixes were verified without changing canonical data or publication.
- This is a pushed implementation checkpoint, **not the B1 freeze or completion**. Extraction quality/replay, accepted variant composition, publication/organize state seams, the final B1/C1 contract, required browser validation and exact-SHA Claude review remain. No panel claim, real-model call, installation or production release is implied.
- The existing MyDataExtractionAdapter gate now admits Sol 6.1 low/medium without changing its incumbent defaults; both extraction/resume payload paths reject a missing Sol 6.1 model identity. Constructor and missing-identity checks were observed RED, then GREEN. Four focused adapter methods and **224 affected adapter/foundation/runtime/conversation tests PASS (1.786 seconds)**. These are isolated adapter guards while package 2's accepted core dependency finishes CI; the named record-driven runtime/budget composition and full Sol 6.1 request proof are still pending. Generic adapter numeric output validation remains unchanged; the fixed named Guide envelope must be enforced by its record-driven runtime composition.
- Build plan v2 was refreshed after Claude's routing update (SHA256 `14213c4fa32ed1eed66958bc1de0ac9183f0e74a7adbc686b6e59f205127c16e`); rationale remains `d6f6151731a471ef53cd173789481e2f66bb428fcbb9a12bc101eb9b76d8c9f5`. Coordination `7ed3050` assigns the owner-only private-preview contract extension in `resume_publication_routes.py` to **B4**, via the ordinary exact-file claim extension and independent review. Preserve every other route/public/publication behavior and held package 6. C14's end-to-end counter acceptance depends on that B4 merge. No such surface extension or file write has occurred yet.

## B1/C1 API contract v1 (frozen by this commit)

### Pre-acceptance review delta to v1

Round-one FAIL is being corrected before any accepted B1/C1 implementation merge. Preserve v1's owner/ref/write semantics, with these explicit extensions/corrections consumed by C1:

- Canonical nodes retain their **saved/hidden base state** regardless of pending updates; `update_waiting` identifies an attached pending update. Rejected updates to saved cards or children appear only in `legacy_outcomes`. Proposal records include their own state. Manual accepted values remain distinct from proposals.
- `counts.updates_waiting` counts top-level items with pending updates, not proposal rows. `child_counts` reports saved/waiting/hidden/skipped/updates_waiting separately, globally and per section. `child_count` remains the all-state total; children do not become roles/cards.
- `Independent Project` maps to Projects when Guide presentation annotations supply that section. Current canonical knowledge values do not store the direct-projector fixture's fabricated `presentation_section`; **n2 belongs to B2 before C2**, mapping actual classification/story binding and saved metadata. `non_tab_items` carries owner-bound Story/Contact separately from unplaced notes; those refs remain available through `working_item` and publication-currentness checks. B2-0's server-qualified first-arrival decision must include existing private content rather than infer new membership from empty counts.
- `saved_revision` remains the opaque command token. `saved_content_version` provides the numeric publication comparison basis; missing basis yields unknown without guessed hex/decimal conversion. `saved_access_revision` is carried, but current `owner_preview` does not expose the matching access revision, so that comparison branch is **not exercised by the standard HTTP path**; no such access-comparison proof is claimed. B2's shared publication basis must cover it. Publication changes derive from the saved draft versus the published copy; unaccepted/declined suggestions never cause changes waiting.
- The route finalizes `working_set_token` **after** publication state is filled. Reads still never write. Pre-B1 rows run the same deterministic binder on a detached copy, and all existing refs/aliases are reserved before minting new ones.
- Privacy purge commits may repair/tolerate invalid Guide identity annotations so deletion still succeeds. This does not invent valid evidence from a corrupt revision history: a remaining history cycle may still make the Guide read unavailable, while the authorized source purge completes and its text stays removed.
- **m6 remains owned by B2 before C2:** per-item current-publication membership and derived draft change count. C1 must not invent those absent fields or a numeric privacy count. **m8 matching cases remain owned by B3:** unequal numbers/qualifiers and different-role notes require actual matching tests. B1 tests preservation/non-merging and real contributing-source removal only.

Correction proof so far: 11 new focused reproductions were observed RED (11 failures/4 errors including table subcases), then 41 focused service/model/HTTP checks PASS in 1.147s. The affected broad regression PASS **527 tests in 49.618s** with fake providers, zero paid calls. The real 8444-shaped HTTP probe freshly publishes with `0000000000000001` draft token, stays published with an unaccepted suggestion, then reports changes waiting after a real draft save. That save test refreshes the access revision after publication rather than sending a deliberately stale pre-publish revision. Separate read-version/identity-alias refinements are also checked. Retained-browser normal/load runs and exact-SHA delta review are still required; no acceptance or merge is claimed.

The full rationale/current source was read before this freeze. This locks the C1-facing interface; it is not source merge, browser acceptance, model qualification or permission to change approved R6q visuals. B2–B4 extend their own contracts deliberately; F1's staged conversion must be written/frozen before B3/C3 and F2 remains the C3 keyboard requirement.

| Interface | Contract |
|---|---|
| `GET /api/resume-intake/me/guide/working-set` | No query parameters or client owner selector. Existing intake flag and authenticated server identity precede retrieval. `200 {success:true,schema_version:1,load_state:"loaded",...}`; backend/unsupported-store failure is `503` with `load_state:"unavailable"` and **no empty counts**. Private/no-store. |
| Section tree | `section_order` is the one approved seven-key order; `sections` contains `{key,label,items,tab_visible,counts}`. Hidden-only sections have no visible tab. `unplaced` retains pending/skipped notes and original units; `legacy_outcomes` labels old declined outcomes without claiming a new saved/hidden decision. |
| Item/reference | `{item_ref,identity_aliases,origin,state,record_type,section,values,saved_revision,parent_ref,proposal_key,revision,proposals,evidence,children}`. Origins `saved/pending/source`; states `saved/waiting/hidden/skipped`. Saved ref is the actual record key. Persisted pending UUID5/ref revisions survive revision/reload; save exposes its pending alias. `source` nodes are retained original units, **not saved facts or confirmable proposals**. |
| Counts | Top-level card counts by state are separate from `child_count`; accomplishment children do not become extra roles. A waiting item is not saved. Multiple proposals on one saved target remain explicit in `proposals`; `proposal_key:null` does not permit a guessed single confirmation. |
| Source/stages | `active_sources` returns owner-bound source key/version/kind, stored reader completeness/pages/units and actual `organization` state. `page_count` comes from the reader's pages, including blank pages; unknown is null. `text_page_count` is separately labeled. A failed organize with no proposal retains original unplaced units. No found-role counts, percentages or simulated steps appear during a pending provider request. |
| Evidence | Only current, version-matching source spans emit exact quotes. Unavailable evidence retains its structural reference, never resurrected text. Revision history accumulates source spans on one item. This projection reads existing stores and never saves/ingests on GET. |
| Versions/receipt | `draft_version`, `lifecycle_epoch`, opaque owner-bound `working_set_token` and the actual stored `last_receipt`. A token/reference is not authorization. Writes continue to use the existing exact command/revision/receipt contracts; navigation and Finish for now never save implicitly. |
| Publication truth | `publication_state` is `unpublished/published/changes_waiting/unknown`, from the explicitly wired existing owner publication authority, not `resume_display` guesses. Failed/unwired authority stays unknown and must never be rendered as "nothing published". C1 uses the approved unavailable/retry handling when that proof is unavailable. |
| Upload/organize | Existing multipart `POST /api/resume-intake/me/submissions`, then `POST /api/resume-intake/me/sources/organize`, with real source key/version and request IDs. Refresh this working set after receipts; do not render only the latest legacy batch overview. Original files/source remain kept on organize failure. |
| Unsent/close | Existing `GET/PUT/DELETE /api/resume-intake/me/draft` and `POST /api/resume-intake/me/guide/status`, exact IDs/revisions and same-origin write protection. Read failures are not an empty/new member; a close records the member's choice, never accepted content. Server-qualified first arrival and once acknowledgment are explicitly B2-0; C1 opens only on member action, and C2 wires auto-open after B2-0. |

Model/runtime composition now consumes the accepted immutable rows behind `services/resume_guide_model.py`'s single provisional medium selection. Named mode requires an explicitly admitted ongoing port; hosted and absent-variant callers retain their paths. Exact outer settings, model/deployment/version/envelopes/prices and acceptance/evaluation ceilings are enforced before reserve/token/HTTP. Purpose is an explicit trusted constructor/composition argument; evaluation cannot borrow the acceptance ceiling. Synthesis high and base service constructor interfaces remain unchanged.

Current fake proof: six model-composition methods, real reader + fake organize PDF stage replay, publication-truth/outage, source-preservation, staged matched-revision evidence and blank-page counts. The PDF proxy proves read success, exact statement/date normalization and an injected provider failure localized to organize with input unchanged. **It does not establish V001's actual provider cause or live model quality.** Automatic pending matching/turn operations remain B3; B1 proves the staged revision/reference/evidence foundation they consume. Before the latest source/publication refinements, 402 affected checks passed; final broad/browser proof is being collected before the B1 exact-SHA review.

Latest pre-freeze verification: **409 affected server tests PASS (11.252 seconds)** and **127 existing intake browser tests PASS normally (234.619 seconds)**, all fake providers. The normal browser run emitted nonfatal teardown warnings about pending route tasks but finished with no test failure. Two simultaneous copies of that browser suite are collecting the required load proof; no claim of their result is made yet. Runtime bytes remain fixed during those runs.

Load proof collected with unchanged runtime: both simultaneous copies PASS **127 tests each**, 239.404 and 237.549 seconds, exit 0. They emitted the same nonfatal pending-route teardown warnings and no test failures. No shared runner/browser module was edited or skipped; browser/provider/SQL/live acceptance boundaries remain distinct. The B1 candidate is ready for the required independent exact-SHA review, not yet accepted/merged or installed.

Custody/import: accepted core was journaled into this worktree at `b8e6ac28776707c596b9b3aa0dded75ac9efd5b7`, operation `b006c8be36d58605699b8d232f6e37ceb915b5adc221cc8acfd193f955a22e12`. The initial refusal was owned generated bytecode and an old registry checkpoint. Accepted `ensure` refreshed exact own custody; only eleven inspected generated `.pyc` files were preserved in stash **`b629c55de5bfafd1d7880191bcc48ae4150dac56`** after automatic policy rejected deletion. No source was discarded, no other checkout changed, no registry was hand-edited and no new worktree/branch bypass was used. Future tests inherit `PYTHONDONTWRITEBYTECODE=1`.

## D4 fixture import and real HTTP nesting proof

The separate same-writer fixture slice passed Claude's independent review at `88b70144`, merged via PR1362 at `723f95c6`, and closed via PR1363 at `c743d27b`. Ordinary C14 fixture-surface restoration PR1365 merged at `73b9dbec31678cff1fc4ddf3519f39aa1f518184` after final CI4570 passed; CI4569 had passed both test jobs but rejected final provenance when main advanced mid-run, so the existing control branch normally merged that accepted main and revalidated. C14 journaled that restoration at `51335865`, preserving all its runtime/evidence bytes and passing the catalog guard2.

B1's native `ensure` refreshed its old registered checkpoint from `b8e6ac28` to the already identical clean local/remote `a1077956`; no code/history reset occurred. Journal operation `1355233fefc83e9923a6d49a36d2544f5e470072e9668f200a6903c77354e10b` imported accepted main at **`3fe4b0b3c2cbda8c9d289cc7fda4607982faa334`**. `git diff --exit-code a1077956 HEAD -- resume_intake_routes.py services` returned0: **all runtime bytes remain unchanged**. Imported deltas are accepted claims, the one fixture parent field and its reviewed guard/evidence/receipt.

New `test_real_http_saved_role_bullet_nesting_per_state_counts_and_no_unplaced_bullet` uses the actual synthetic8444-shaped server, real private HTTP route and owned canonical role/bullet records. It asserts exactly one saved top card, one saved child, all other per-state counts zero, matching global/section child counts, the actual parent/reference/literal wording and no unplaced bullet. It also reads **`GET /api/resume-drafts/me` over real private HTTP** and verifies the saved bullet's `parent_key`, closing Lane D's API-dependency proof once this B1 candidate merges. The same nesting guard was **RED** using the exact old Git fixture loaded only into a child Python process with unchanged `a1077956` runtime (top saved2, child0, bullet unplaced); no fixture file was overwritten. It is **GREEN** with the accepted fixture. Final focused service/model/catalog checks: **40 PASS in4.146s**, fake providers.

Current-target required browser proof: **152/152 normal PASS in332.774s**, and two simultaneous copies **152/152 each PASS in331.334s/326.025s**, zero errors/failures/skips. Logs: `X:/PeerSlate/ChatGPT/evidence/mvp1-fixture-parentkey-2026-10-13/b1-browser-{normal,load-1,load-2}.log`. Runtime and browser-test/runner bytes stayed unchanged. The added non-browser draft-HTTP assertion also passed in the final focused run. Complete D4 delta self-review and whitespace checks found no outstanding writer finding; independent D4-only exact-SHA recheck remains required. No merge, installation, real provider quality or production release is claimed.

Carry-forwards stay explicit: B2 before C2 owns m6 per-item publication membership/count, n2 real knowledge classification/story binding, and the shared publish basis including Story/Contact, binding changes, eligibility/blocked items and the unavailable access-revision comparison. B3 owns unequal-number/qualifier/different-role matching and the corrupt-history repair/operator path for ordinary saves (purge tolerance is not that complete repair; never silently discard accepted facts). **B2-0** is first in B2 per actual manager ruling `1930d36`, `Shared/handoffs/2026-10-13_claude-pc_to-codex-pc_C1-first-arrival-contract-answer.md`: owner-qualified read-only eligibility plus idempotent shown/dismissed/started acknowledgment on existing Guide state, no new store/provider/migration/content acceptance. C1 automatic opening stays off; C2 wires the once behavior before Pete's8444 pass. This creates no B1 runtime delta and does not broaden the D4-only narrow recheck.


## Independent B1 acceptance

Claude reviewer `session:9fb18da7-d312-4e90-a956-7f3718e5969f` independently PASSed exact `b0133adef05dcb9af5e479729a48d94bb380ded4`, read after a fresh pull at coordination `fe24d43` (review introduced at `9d3ec1f`). D4 is resolved; together with the accepted `a1077956` delta, B1 is accepted at this SHA. Reported review window is approximately17:20–17:55Z on2026-10-13, not precise time telemetry. Independent runtime byte comparison and HTTP RED/GREEN reproduce the writer's result;97 focused suites pass.

The independent whole no-Playwright run was7,653/271 skipped with36 failures/errors versus base35. The one extra unchanged Ask Pete credential-deadline test passed3/3 alone; reviewer classified it as load-sensitive and not attributable to B1. Retain this explicit limitation; no test deadline is changed and no green whole local-suite claim is made. Current152 normal/concurrent browser proof is accepted.

All7 fixed source criteria are mapped to exact-candidate semantic evidence. The acceptance helper and merge preflight must pass on this receipt/evidence tail; normal current-target Azure PR CI then remains required before repository merge. No merge, installation, real model-quality or production release is claimed. The server claim stays active for B2–B4. The actual `c14a852` manager reply confirms the same-branch plan-only PR → accepted evidence-only squash → native journal import/bind accepted main `plan_sha` route before every later round's code, with criteria/baseline and all existing checks retained.

## B2 pre-code round plan

**Current outcome:** B1 is accepted at PR1366/main `80de9360f029f717e731488d0ef65435446607df`, required CI4574 succeeded. Its independently reviewed runtime/test bytes are unchanged. Native journal `7ebe4232d965f476c7a18ba4f399fca7bdffccf7228913b039602984d805956e` imported that main into this existing branch at `0393d1c2a425dc07e8ba095fe02df966621895e4`, with an identical tree. The preceding B1 acceptance JSON is retained as historical JSON; its original active record and review receipt remain at accepted main80de9360. The single active acceptance record below belongs to B2; it does not retract B1 acceptance or claim B2 completion.

**Authority and dependency sequence:** original Pete package3 assignment remains active. Claude's actual correction `fb97e61`, with dry-run proof `fffad2e`, supersedes the earlier `c14a852` plan-PR route. The plan needs one accepted-main parent, an evidence-only delta and ancestry in the later candidate; the plan itself need not merge to main. The actual prepared plan is therefore adopted into this existing branch by an ordinary two-parent merge and bound below before B2 code. No reset, rewritten history, new workstream, plan PR or delivery-tool/policy change is required.

Claude's actual `f2f91cf` reply settles the shared publication basis: B2 first takes exactly `services/resume_publication_service.py` and `tests/test_resume_publication_service.py` through normal exact-file extension, then extracts one genuinely read-only review/candidate seam used by explicit review/commit and Guide GET. Explicit review still records its pending review; GET does not. After B2 acceptance, native scope release returns these two unchanged-at-main surfaces for package6. They have not been extended or written by this preparation. C2 and later D2/6 consume the accepted shared table, order and publish basis; no unowned page or publication route is edited here.

**Execution steps:**

1. Dry-check the actual prepared evidence bytes against the acceptance predicates. Create an evidence-only plan commit with accepted main as its single parent; bring it into the existing branch with an ordinary merge, push normally and bind `plan_sha` before implementation. The usual exact-candidate review, receipt, acceptance, merge preflight and CI apply at B2 completion; the superseded B1 receipt is not used to deliver the new round plan.
2. Complete the normal two-file claim extension and import its accepted main before writing either publication file. Keep one writer and preserve existing public behavior, policy, draft/media checks and commit semantics.
3. Add meaningful RED cases first, then implement B2-0 first-arrival eligibility/acknowledgment, reversible review/hide/show, the shared essentials/70-word cap/types/order and owner-bound evidence/highlight references on the existing state/proposal/draft foundations. Preserve required member choices, unknowns and manual precedence; no second store, extractor or migration.
4. Extract the shared side-effect-free publication seam and derive membership, per-item published/changed flags, change count, Story/Contact/binding and blocked/ineligible reasons from exactly the actual publish candidate. Remove the dead knowledge-field/access-revision overclaims rather than inventing DTO fields. Failure stays unknown; a pending suggestion alone is not an unpublished change.
5. Self-review the complete owned delta, run affected regressions and retained normal/concurrent browser proof, freeze/push the exact candidate, obtain Claude's independent exact-SHA PASS, map all criteria, pass acceptance/merge preflight and current-target Azure CI. Merge only accepted B2; then perform the exact two-file release and report the accepted dependency to C2/Lane D. F1/F2 conversion/menu work remains B3/C3; B3's matching/corrupt-history repair and B4's private-preview/counter/live-words work remain later rounds.

**Baseline before B2 code:** the selected current Guide/draft/publication service and route suites pass109/109 in2.510s at tree-identical accepted B1 source, exit0. Command and retained raw log are below. The expected injected visitor-AI-unavailable log is a test case, not a paid call or product error. No B1 load proof is rerun as preparation.

**Jev checkpoints:** scope/sequence is settled by Pete's assignment and actual manager rulings, so no advisory choice overrides it. B2 baseline/evidence prioritization has meaningful alternatives and source-backed evidence that could change checks; free status `286dbc4d-9092-4373-9985-9f7bea57aa83` reports `usable_now=false`, `ongoing_paused_transport_failure`. No evaluation, retry, wait, settings/allowance change or alternate connection. Fallback selects the four directly affected existing Guide/draft/publication suites and retains every mandated criterion. Future regression/review judgments follow the same required checkpoint rule.

**Holds:** fake providers/$0; no model adoption or live quality claim, schema, identity, credentials, product release, installed-site admission or personal-site stop. The model runner's actual terminal Interview handback `fbcaeb6` resolves the ten-call scheduling request; this builder makes0 live shared calls, and any later use still needs its own real arrangement. Trust/header/footer/fonts/media/evidence-companion/Pete JSON/logo custody remains unchanged. Existing C14/C1 work continues under its own claims; this plan grants it no acceptance.

```json
{
  "schema_version": 1,
  "package": "PS-GUIDE-SERVER-001",
  "plan_sha": "f361b7b8238d2be2f56d072439920d03a1caa223",
  "candidate_sha": "492b2643fe53b934b80bde01c5f376207c2cf1bf",
  "baseline": [
    {
      "command": "X:/PeerSlate/runtimes/development/Scripts/python.exe -B -m unittest tests.test_resume_guide_service tests.test_resume_draft_service tests.test_resume_publication_service tests.test_resume_publication_routes -q",
      "exit_code": 0,
      "observation": "109/109 PASS in2.510s before B2 code at0393d1c2, tree-identical to accepted B1 main80de9360. Process-local CI placeholder key and fake/in-memory providers only. Raw log X:/PeerSlate/ChatGPT/evidence/mvp1-fixture-parentkey-2026-10-13/b2-precode-baseline.log."
    }
  ],
  "criteria": [
    {
      "id": "b2_first_arrival",
      "expected": "B2-0 exposes owner-qualified eligibility only after a complete read proves no Guide state/dismissal, private draft or My Data content; GET is read-only. Existing Guide command/state storage idempotently acknowledges shown/dismissed/started without inventing completion or canonical content.",
      "verification": "New/existing member, unreadable authority, dismissal, reload/second-tab, replay and foreign-owner cases; instrument GET for zero repository/provider writes. C2, not B2, wires once-only automatic opening."
    },
    {
      "id": "b2_review_hidden",
      "expected": "Explicit revision-checked owner decisions preserve stable identity and truthful receipts. Saved hide/show restores saved/excluded state; pending hide/show is reversible hidden/waiting and never auto-saved or rejected. Navigation never confirms, and hiding a published item leaves its public copy until explicit Publish changes.",
      "verification": "Saved/pending by hide/show table, repeated and stale commands, another owner, later manual edit, reload, no-write navigation and unchanged publication; exact stored result/record revision proof."
    },
    {
      "id": "b2_essentials",
      "expected": "One shared server essentials table implements approved type rules: credential name/issuer/year, education institution/graduation year, publication title/publisher/year, membership organization plus joined year or years, project name/one-line description and other types' name/label. Missing essentials return explicit missing_required_fields; optional blanks do not invent questions or block navigation.",
      "verification": "Exactly-essential save and one-at-a-time missing-essential refusal for every supported type; status/date and unsupported-type cases, optional blanks, private manual and proposal confirmations using the same table; existing canonical/privacy checks retained."
    },
    {
      "id": "b2_impact_cap",
      "expected": "Impact Statement saves enforce at most70 whitespace-separated words on every save path, with impact_statement_too_long and actual count at71. Over-cap member/import originals remain recoverable and waiting; AI-generated output is validated before presentation and never silently truncated.",
      "verification": "70/71 boundaries, whitespace, hyphenated/accented words, private manual/proposal/import paths and fake model output; refusal/repair keeps exact originals and creates no canonical write until explicit valid confirmation."
    },
    {
      "id": "b2_types_order",
      "expected": "Projects, Looking Ahead and real stored knowledge signals use the existing canonical/draft foundation; n2 handles classification plus the actual story binding, with no fabricated presentation_section value. One approved section order serves all consumers. Projects need a name/one-line description, category optional, dates optional and up to3https links; Looking Ahead is optional and at most120characters. Story/Contact retain deliberate non-tab semantics.",
      "verification": "Actual manual pre-B1 knowledge and accepted-history rows, bound/unbound Story, Contact, Projects/Looking Ahead including120/121characters, reload and unknown classification; one shared order and safe optional category/link/date validation with no fetched links or source loss."
    },
    {
      "id": "b2_links",
      "expected": "Skill-to-bullet and highlight-to-bullet evidence are owner-bound references to the real saved bullet, never copied drifting text. Missing/stale/hidden/foreign or wrong-type targets cannot acquire a valid link or imply publication/visitor-AI permission.",
      "verification": "Valid saved reference, foreign owner, wrong type, changed revision, hidden/removed target and reload; source text and manual edits remain canonical, read/projection does not write or widen access."
    },
    {
      "id": "b2_publish_basis",
      "expected": "One genuinely read-only publication review/candidate seam returns exactly what Publish changes would publish, including membership, per-item published/changed flags, change count, Story/Contact/binding, blocked/ineligible reasons and basis revision. Explicit review/commit keep their behavior; Guide GET creates no pending review. Missing/malformed authority stays unknown.",
      "verification": "Instrument repository/provider/pending-review writes; compare seam versus actual review/commit for content, Story-binding-only change, contact, ineligible/blocked entries, permission revision and another owner. Existing publication service/route behavior remains; no unreachable access-revision proof or inferred change count."
    },
    {
      "id": "b2_regression_review",
      "expected": "Affected server and retained browser regressions pass without weakening their runner; no held/unowned surface changes. The exact source candidate receives Claude's independent PASS. Current-target CI/merge and the mandatory subsequent two-file native release remain separate external delivery gates, never inferred from source-test acceptance.",
      "verification": "RED/GREEN cases, focused/shared publication/draft regressions, retained browser normal plus concurrent proof, complete diff self-review and exact-SHA independent receipt. Source acceptance/merge preflight and actual Azure policy CI guard delivery; record the mandatory post-merge scope release separately."
    }
  ],
  "checks": [
    {
      "criterion_id": "b2_first_arrival",
      "result": "pass",
      "kind": "automated",
      "candidate_sha": "492b2643fe53b934b80bde01c5f376207c2cf1bf",
      "source_ref": "coordination:bffe29d:Shared/handoffs/2026-10-14_claude-pc_to-claude-pc_REVIEW_PS-GUIDE-SERVER-001_B2_round3.md + coordination:4bedbba:Shared/handoffs/2026-10-14_claude-pc_to-claude-pc_REVIEW_PS-GUIDE-SERVER-001_B2_round2.md (criteria table) + tests.test_resume_guide_service",
      "observed": "Independent HTTP spies: first-arrival GET writes nothing on intake/draft/policy/publication and leaves pending reviews unchanged; ack is idempotent; a new member's first GET during another member's held organize finishes in 0.0 s."
    },
    {
      "criterion_id": "b2_review_hidden",
      "result": "pass",
      "kind": "automated",
      "candidate_sha": "492b2643fe53b934b80bde01c5f376207c2cf1bf",
      "source_ref": "coordination:4bedbba:Shared/handoffs/2026-10-14_claude-pc_to-claude-pc_REVIEW_PS-GUIDE-SERVER-001_B2_round2.md (b2_review_hidden PASS) + coordination:bffe29d:Shared/handoffs/2026-10-14_claude-pc_to-claude-pc_REVIEW_PS-GUIDE-SERVER-001_B2_round3.md",
      "observed": "Hide leaves publication store, guest read, policy flags and visitor-AI evidence byte-identical; stale Show and stale basis refuse; Publish of the exact basis removes the item and a later Show keeps visitor AI off; Hide/Show during organizing no longer discards the organize result."
    },
    {
      "criterion_id": "b2_essentials",
      "result": "pass",
      "kind": "automated",
      "candidate_sha": "492b2643fe53b934b80bde01c5f376207c2cf1bf",
      "source_ref": "coordination:4bedbba:Shared/handoffs/2026-10-14_claude-pc_to-claude-pc_REVIEW_PS-GUIDE-SERVER-001_B2_round2.md (M3 resolved) + tests.test_living_resume_editor_service",
      "observed": "Every supported type saves at exactly its essentials and refuses one missing essential by name; planned/in-progress credentials save with name+issuer and no year; non-credential rows unchanged."
    },
    {
      "criterion_id": "b2_impact_cap",
      "result": "pass",
      "kind": "automated",
      "candidate_sha": "492b2643fe53b934b80bde01c5f376207c2cf1bf",
      "source_ref": "coordination:4bedbba:Shared/handoffs/2026-10-14_claude-pc_to-claude-pc_REVIEW_PS-GUIDE-SERVER-001_B2_round2.md (b2_impact_cap PASS) + tests.test_resume_intake_service + tests.test_living_resume_editor_service",
      "observed": "70 words save, 71 refuse with impact_statement_too_long and actual_count 71 (hyphenated/accented counted); Looking Ahead 120/121 UTF-16; originals kept."
    },
    {
      "criterion_id": "b2_types_order",
      "result": "pass",
      "kind": "automated",
      "candidate_sha": "492b2643fe53b934b80bde01c5f376207c2cf1bf",
      "source_ref": "coordination:4bedbba:Shared/handoffs/2026-10-14_claude-pc_to-claude-pc_REVIEW_PS-GUIDE-SERVER-001_B2_round2.md (M4 resolved: stored order on read) + tests.test_resume_publication_projection",
      "observed": "One shared section order for Guide/basis/new Publish; existing published snapshots keep stored order on owner/guest/SQL reads until explicit Publish; Projects fields/links validated and links kept out of model context; Story/Contact non-tab."
    },
    {
      "criterion_id": "b2_links",
      "result": "pass",
      "kind": "automated",
      "candidate_sha": "492b2643fe53b934b80bde01c5f376207c2cf1bf",
      "source_ref": "coordination:4bedbba:Shared/handoffs/2026-10-14_claude-pc_to-claude-pc_REVIEW_PS-GUIDE-SERVER-001_B2_round2.md (b2_links PASS) + coordination:bffe29d:Shared/handoffs/2026-10-14_claude-pc_to-claude-pc_REVIEW_PS-GUIDE-SERVER-001_B2_round3.md (908 focused) + tests.test_resume_intake_service.GuideReferenceCommandTests",
      "observed": "References resolve only to the owner's saved visible records of the right type; foreign/stale/hidden/wrong-type refuse; deletion prunes in the linked transaction; no copied text stored."
    },
    {
      "criterion_id": "b2_publish_basis",
      "result": "pass",
      "kind": "automated",
      "candidate_sha": "492b2643fe53b934b80bde01c5f376207c2cf1bf",
      "source_ref": "coordination:4bedbba:Shared/handoffs/2026-10-14_claude-pc_to-claude-pc_REVIEW_PS-GUIDE-SERVER-001_B2_round2.md (m1 resolved) + tests.test_resume_publication_routes.ResumePublicationRouteTests.test_codec_blocked_review_names_each_blocked_item_and_saves_nothing",
      "observed": "The read-only basis creates no pending review and its candidate publishes exactly (next count 0); unknown/blocked give null counts; the explicit review 409 names blocked_items with refs and reasons only."
    },
    {
      "criterion_id": "b2_regression_review",
      "result": "pass",
      "kind": "automated",
      "candidate_sha": "492b2643fe53b934b80bde01c5f376207c2cf1bf",
      "source_ref": "coordination:bffe29d:Shared/handoffs/2026-10-14_claude-pc_to-claude-pc_REVIEW_PS-GUIDE-SERVER-001_B2_round3.md + X:/PeerSlate/Claude/reviews/b2-builder-evidence/round3/r3-discover.txt + X:/PeerSlate/Claude/reviews/b2-builder-evidence/round3/r3-strict-load1.txt + X:/PeerSlate/Claude/reviews/b2-builder-evidence/strict152-normal.txt + coordination:f991c23:Shared/handoffs/2026-10-14_claude-pc_to-claude-pc_REVIEW_PS-GUIDE-SERVER-001_B2_round4-recheck.md",
      "observed": "Independent exact-SHA PASS at 5730a316; strict 152 normal and two-copy load pass with the runner unchanged; full no-Playwright discover failure set identical to base main; provider-lock audit 0 held and lock-order audit 0 inversions; matrix 8/8 with 16 failures on round-1 source. Round-4 recheck PASS at 492b2643 for the test-only CI-race precondition."
    }
  ]
}
```

## B2 plan ancestry admitted (before code)

Actual source `656b5123` was dry-checked in a throwaway **bare** repository, no worktree or product ref change: plan single parent80de9360, fixed evidence file only, clean merge-tree, plan ancestor of a throwaway later candidate and all8 criteria/baseline unchanged. Proof `X:/PeerSlate/ChatGPT/evidence/mvp1-fixture-parentkey-2026-10-13/b2-plan-dryrun.json`; this is plan-predicate proof, not synthetic B2 test acceptance. During preparation, authoritative main advanced disjointly to accepted D1 `996ea385`; the actual predicate is parent-on-main ancestry, which80de9360 still satisfies. The initial dry script's equality assertion was narrowed to that exact predicate before any clone/object/adoption side effect.

After a fresh successful write preflight, real plan **`f361b7b8238d2be2f56d072439920d03a1caa223`** was created with tree01554e50 and sole parent **`80de9360f029f717e731488d0ef65435446607df`**. Ordinary merge **`e409e1584223080377d408c446b1daeeb7a421c4`** has parents656b5123 and that plan, is pushed normally and preserves the exact prepared tree. Older drafts remain ancestors. This evidence binds `plan_sha`; baseline/criteria are byte-semantically unchanged from the real plan. The actual manager answer resolves the earlier plan-admission question; no gate repair or waiver is needed. B2 runtime/test code has not started, and the two publication files still await their ordinary claim extension. The existing B1 review receipt remains historical until a genuinely reviewed B2 candidate replaces it.

## B2-0 implementation frontier (unreviewed)

Later checkpoint: `ff4a43dc9600ff3bf1e072d6c5a7d08cf4ce4aa9` adds explicit dismissed/started choices during catalog outages; 301 affected regressions pass (14.083s). The publication assembly/validation now has a shared `read_review_for_owner` seam, with explicit `review_for_owner` retaining its pending-review cache. The 89 service/route/contract tests pass (0.616s, `b2-publication-read-seam-checkpoint.log`). This is an unfinished source checkpoint, not B2 acceptance or an independent review.

Expiry regression tests now reproduce the actual issue in both caller paths: `IntegratedDraftPublicationTests.test_read_review_does_not_persist_expired_policy_cleanup` and `GuideFirstArrivalTests.test_first_arrival_does_not_persist_expired_canonical_cleanup` each fail on the unexpected policy `save_owner` (2 failures, 1.657s; external `b2-expiry-readonly-red.log`). Preserve this RED checkpoint before native main reconciliation; it is deliberately unfinished and must turn GREEN before source review. Current C14 fixture release operation `951096c82e58621eed61ba85b650d942a7f886d721aae48fe63ea7522b13f608` freezes unchanged clean/pushed51335865; claim-only candidatef1539012, PR1369, ordinary required CI. No fixture or unclaimed policy code has been edited.

The shared publication seam now requires an explicit read-only policy reader for both initial assembly and `OwnerPolicyPort` validation rereads; it refuses a legacy/unqualified reader without invoking it or caching a pending review. The new refusal test was RED (no exception, 1.865s) then GREEN (1.833s) after the owned adapter change. This is still an intermediate checkpoint: the primary policy reader and fixture must be reserved, implemented and tested before the full suite can pass. Preserve legacy direct policy cleanup behavior and existing explicit-review cache/commit semantics. No B2 acceptance is asserted by this one GREEN test.

## Expiry writes removed through the canonical read authority

C14's unchanged fixture release is accepted: PR1369/main **`94cd8614cfd01e7adbc6554380731f42241b8707`**, full required CI4589 succeeded2026-10-14T02:13:10.3319759Z, no schema/deploy. Native release951096c8 completed, and C14 journal `ea0fec73fb75884184bd48cd99cc73934bf5d730759d65ec1325f13c05157994` imported the reduction at **`9b2a5360ee2a8c2f66c257e58161c74cbfe7a0fc`**, preserving its retained implementation. B2's ordinary three-file extension is accepted: PR1370/main **`1df2560a15d53678c958284a16e61a5b2d4c6216`**, candidate331ca55a, CI4592 succeeded2026-10-14T02:29:08.9347215Z, no schema/deploy. It reserves the primary policy service, its existing test module and the shared fixture. The control lease was released. Native B2 journal `703e5eb1cd55eae81aefd6aa5d9a39465e501530e8ac7399676c0ac03d561bfd` imported main into the same branch at **`73a260f828b91e94f4a8045bf747fc06999b86f6`**. A fresh write preflight passed before any of those3 source paths changed. The fixture returns to C14 after accepted B2; the2 publication files retain their separately required post-acceptance release.

`EntryPolicyService.read_entries()` uses the existing expiry calculation on a copied snapshot without saving. `read_publication_entries()` uses that same path for snapshot stores and the existing owner-scoped publication read for the SQL-shaped port. Direct legacy `list_entries()`/`get_entry()` cleanup behavior remains. The shared canonical fixture uses the primary read method, retaining its exact parent-key and alias mappings. Publication initial assembly and every validation reread now use the explicit read-only policy adapter; explicit review still records its pending review and commit semantics are unchanged.

The2 primary tests were RED for the absent reader (2 errors,0.042s), then all **5 targeted cases GREEN in1.591s** after implementation. They cover a mutable load result that must remain untouched, zero saves, expiry output parity, owner isolation, preserved explicit legacy cleanup, SQL-shaped read delegation without load/save/command, caller purity and unqualified-reader refusal. The earlier2 actual caller-save failures are resolved. External patch files initially had Windows line endings; strict apply refused before product changes. Normalizing only those external patch files allowed strict apply; no whitespace/context bypass was used.

Affected server regressions: **475/475 PASS in15.258s**, covering Guide/model, intake/runtime/routes/fake-SQL, draft/routes/fake-SQL, real catalog guard, entry-policy/service/routes/fake-SQL, and publication/service/routes/contracts/adapters/repository/projection/fake-SQL. Retained strict browser runner: **152/152 PASS in297.481s, zero skips/failures/errors**. Logs are `b2-primary-readonly-red.log`, `b2-primary-readonly-green.log`, `b2-readonly-server-regressions.log` and `b2-readonly-browser-normal.log` under the existing external evidence folder. Concurrent browser proof is next on the immutable checkpoint; it is not yet claimed here. These are synthetic/local proofs, not real SQL-engine, installed-site or production acceptance.

B2's full8-criterion source acceptance remains unfinished: shared publish-basis metadata/GET consumption, hide/show/essentials, Impact cap, new types/order/links and independent exact-SHA review still remain. The current old B1 receipt is history. No B2 completion checks or candidate receipt are fabricated. A bounded representation question was published at coordination `f7735803cbcfb23d95072e67516334a494cfc71d`; only the unsupported new-type mapping awaits that answer, while independent assigned work continues.

## Read-only publisher basis metadata frontier

The existing shared validated candidate now supplies `read_publication_basis_for_owner`: exact review packet/digest, proposed display/visitor membership and wording, actual per-item published/changed flags, Story binding, profile reference, visible media, blocked/deleted/unsupported reasons and a basis revision. Additional owner-authority reads check policy refs, draft/publication revisions and sharing epoch against that same candidate; they do not run another extractor or create committed evidence. Missing/malformed/stale reads return unknown with null counts/membership, rather than an empty publication. Explicit review retains its pending cache; commit remains explicit. The Guide GET integration and Contact mapping are not claimed complete by this helper.

The first5 tests were RED for the missing method (1.633s). They now pass, including equality with the actual review packet, a real commit, an unchanged post-publish count, one Story-binding-only change, blocked/deleted reasons, malformed authority and another owner. The first implementation exposed a false difference between missing optional fields and stored nulls after draft consumption; a real round trip reproduced it and the comparison now treats missing/null as the same visible value. A later media test caught equivalent integer/decimal-string versions counted as changes; the reader now compares/transports exact decimal tokens without JavaScript precision loss. The publish path retains its prior native representation through one shared media projection helper.

The permission test initially assumed an old published access revision after a real restriction. Inspection showed the actual linked restriction rebases the committed evidence; the corrected test proves that reachable state and the owner preview's real visitor-AI field. No unreachable synthetic access-revision gap is used. A separate real competing draft write after the candidate read produces unknown, not an outdated count. **138 publication/service/route/contract/adapter/repository/projection/fake-SQL regressions PASS in0.515s**, including8 new basis cases. External logs: `b2-publication-basis-red.log`, `b2-publication-basis-green.log`, `b2-publication-basis-revisions-red.log`, `b2-publication-basis-regressions.log`. These remain local/fake-port evidence, not SQL-engine qualification. The completed B2 candidate still needs full retained normal/concurrent proof; do not replay full interim browser runs merely for each helper checkpoint.

Jev checkpoint `b2-publication-basis-metadata`: current validated manifests and actual stored `PublicationEvidenceVersion` fields supply the comparison; no fabricated committed-evidence object or guessed opaque token is created on read. The choice was between using the validated proposal plus verified current authority and constructing future committed evidence. Statusfcbdea15 remains unusable/paused, so the source-backed fallback keeps those meanings separate and records null/transport/revision edge checks. No evaluation/retry/settings change.

Actual mapping answer **coordination269ab17** was read after fresh pull14410c2, resolving questionf7735803. Implement credential `qualification_kind`, local project fields/links, optional local education title and precise year/month mappings as ruled. New qualification kinds/project extras keep named publishing blockers until package6's codec work; unqualified SQL remains closed with input kept. Preserve model request bytes and the approved award mapping. The same manager's overnight handoff14410c2 reports Pete's no-production-tonight hold, Claude's temporary pause, no model switch and no8443 stop before exact review/Pete presence. This builder's production authority was already withheld; no new release/configuration/credential authority is inferred. Silent implementation details may be recorded provisionally for later Claude confirmation; new product/visual/money/release decisions are not granted by that note.

## Local type normalizers and actual canonical-port integration

The ordinary4-file editor/projection extension is accepted: PR1371/main **`af9ef505dc1be3007f58a941396d53575e8f550c`**, candidate d4f0376d, required CI4596 succeeded2026-10-14T04:07:16.2782335Z, schema/deployment skipped. Native control was released; journal `841a1b1af09796a31367b4ebfa2202c0ef749d2f879b999609afc3218bf5e87d` imported it into the existing branch at **`18b42028923311f8345a1ff264e70e1dd96c4153`**. Fresh write preflight passed before the new normalizer/test surfaces changed. No shared section/projection implementation is claimed yet.

Credential kind is optional and closed; absent legacy input inserts no new kind field. Membership accepts the real organization/date with no invented name. An explicit null can clear a kind. Education's `require_title=False` is an explicit local normalizer mode; its default remainsTrue for the SQL editor. Projects have the ruled name/one-line summary and optional fields, at most3 distinct HTTPS/host links, and no stored defaultOther. Dates use the existing precision vocabulary. Supplied optional clears remain null/empty rather than being silently dropped. Links are parsed as strings, never fetched. Partial-intent normalization retains only supplied fields.

The private draft accepts local projects, qualifications and untitled education. The actual shared EntryPolicy canonical port now carries kind, project category/organization/list links and institution/year education without an invented title, using the same local normalizers and existing aliases. Legacy absent-kind/basic primary paths retain their behavior. SQL-bound draft/editor/policy calls reject the unsupported local fields before procedures and keep input; no schema or codec extension is introduced.

Seven new editor tests were RED for missing support, then GREEN; a separate optional-clear test exposed dropped clear keys and was fixed. Draft type groups were RED, then local create/reload and three SQL refusals passed. The actual `SharedMvp1Fixture` integration was RED for3 types, then the combined primary/editor/new-draft group passed **65 tests in1.621s**. Broader coupled regressions passed **483/483 in12.211s**; after the final explicit-null assertion and whitespace SQL-title guard, **78 focused primary/editor/draft/route/fake-SQL checks passed in0.092s**. Logs: `b2-local-editor-red.log`, `b2-project-clear-red.log`, `b2-local-editor-regressions.log`, `b2-local-draft-red.log`, `b2-local-draft-green.log`, `b2-local-primary-integration-red.log`, `b2-local-primary-integration-green.log`, `b2-local-types-regressions.log`, `b2-local-types-final-focused.log`. A test initially repeated a keyword in its own membership fixture; that setup issue was corrected, not counted as a product defect.

This is foundation work, not the complete essentials workflow, Guide mutation HTTP contract, publishing codec blockers or shared section order. The plan's8 source criteria/baseline are unchanged and no B2 acceptance checks/receipt are fabricated. Shared provisional details and the remaining Contact mapping question are at coordination **`2fb1f3f1d08e144e24f40fd3d43a503d9c09fa15`**; confirmations/SM3 home ETA remain separate from this ongoing implementation.

## Shared ordering, real knowledge signals and Contact basis

The seven core definitions now live once in `resume_publication_projection`; Guide aliases them and uses its classification/order functions. Stored credential kind supplies Publications/Memberships, with only encountered optional groups appended (a real Languages group precedes them); no phantom tab is created. Core order stays fixed. Structured record type wins over a false placement hint. Saved personal knowledge becomes Story only through the actual private draft binding; pending Story remains a proposal. Approved award/summary/project placement is retained. The existing Contact knowledge marker is recognized separately from sign-in/profile identity. Looking Ahead is non-tab. The private canonical read annotates the real binding without storing a fabricated presentation_section. Project name maps to the existing codec title slot; no codec version/field expansion is made.

The3 shared-function/order/name tests were RED, then **52 projection/Guide/catalog checks PASS in3.964s**. Two additional real server/canonical tests prove local qualification groups and unchanged reads, plus unbound personal knowledge/actual Story binding/Contact non-tab behavior; the combined targeted group passed **9 in2.473s**. The Contact basis case was RED for the missing field, then the descriptor reports actual proposed/published contact-entry membership and a real private wording change while the published copy stays unchanged. It never borrows a sign-in email. Contact mapping is resolved by ARCHITECTURE §3's actual type table and `_apply_record_decision`'s approved Contact/work mapping, not by a new product choice.

Final affected section/Contact/publication/Guide/intake/draft/catalog regression group: **369/369 PASS in13.679s**. Logs: `b2-shared-order-red.log`, `b2-shared-order-green.log`, `b2-shared-order-real-api.log`, `b2-contact-basis-red.log`, `b2-shared-section-contact-regressions.log`. Additional group encounter ordering remains the recorded overnight provisional interpretation for Claude to confirm. The remaining essentials/mutation/limits/links/codec/GET integration and complete B2 normal/concurrent/exact-review gates remain unfinished; no full B2 acceptance is claimed.

## Guide essentials and explicit manual-save guard

One shared Guide essentials helper now names required editor fields per type/kind. It does not make optional blanks into questions. Guide date input keeps year/month precision while using the existing ISO representation; education uses no invented title/degree. Defaults follow269ab17 and do not overwrite explicit planned/in-progress credential status. Named Impact/Looking Ahead checks retain originals and report actual counts (70 whitespace words;120 UTF-16 units, matching the existing browser field measure). This is Guide workflow validation, separate from generic private editor behavior.

An explicit `guide_review:true` draft command invokes this helper after existing receipt classification. Only this new mode adds the mode/optional section to the normalized command digest; legacy command bytes stay unchanged. Save merges the current canonical/private values and protects an existing named Impact/Looking Ahead section from a renamed-title bypass. SQL-bound stores refuse the unqualified mode before procedures. Typed required-field/limit metadata propagates through the existing draft route; it does not publish or dispatch a provider.

The3 helper cases were RED, then the combined local helper group passed **10 in0.046s** after fixing inherited error-code initialization. A manual create case was RED for the generic error, then helper/manual/route checks passed **21 in0.110s**. Final **211/211 PASS in3.822s**, including a real HTTP missing-year400, actual71/70-limit400, zero policy/draft saves for both failures, and successful precise-year/titleless private education200. Logs: `b2-guide-essentials-red.log`, `b2-guide-essentials-green.log`, `b2-guide-manual-red.log`, `b2-guide-manual-green.log`, `b2-guide-essentials-manual-http.log`. A no-op route-test patch initially used a nonexistent import anchor and changed no file; the actual test insertion used the inspected class anchor.

Proposal confirmation, imported/model overlength repair, optional Looking Ahead clear behavior, other-label-only knowledge mapping, full visibility/link commands, codec blockers and Guide GET consumption still need implementation/verification. This manual helper is not all-path B2 acceptance. No source criteria, baseline or old B1 receipt were rewritten to manufacture completion.

## Explicit Guide proposal confirmation uses the same guard

The intake decision accepts the additive explicit Guide mode and selected section, with mode/section included in its request digest only when present. Existing receipt classification remains before content application; legacy bytes stay unchanged. The application copy carries workflow context without storing a fake canonical field. The same essentials/date/limit helper runs for new facts and merged private updates. Derived precision/status accompanies a normalized year through the draft call. Existing named content and approved placement prevent a wrong-section/title limit bypass; a mismatched structured-type section requires staged conversion rather than a false save. Approved legacy knowledge placement labels stay as the existing names. Local project/kind fields are closed; SQL units refuse unsupported data/mode with input kept. The existing decision HTTP route propagates required fields and actual count metadata.

Two new cases were RED for generic validation, then GREEN: missing year leaves the exact proposal pending with no fact; a valid year saves the same proposal privately once and an exact retry replays;71-word Impact preserves the pending original and returns the actual count. **325 coupled checks PASS in13.181s** before the final section/precision refinements. Real HTTP plus the two cases passed **3 in0.543s**; final intake/route/editor/draft group **186/186 PASS in10.426s**. Logs: `b2-guide-proposal-essentials-red.log`, `b2-guide-proposal-essentials-green.log`, `b2-guide-proposal-essentials-regressions.log`, `b2-guide-proposal-http.log`, `b2-guide-proposal-final.log`. A no-op route patch guessed a missing body anchor and changed no file; the inspected function/class anchors were used afterward.

This is not complete B2 acceptance. Imported/model-output and remaining limit paths, optional clear/name-only mapping, visibility/links, codec blockers and Guide GET integration still need their named checks. Full retained normal/concurrent proof and exact Claude review remain required on the completed candidate. The source plan/baseline/checks are unchanged.

## Named publication-format blockers preserve the local data

Following269ab17, the same review seam refuses selected Publication/Membership kinds and unsupported nonempty verification/project fields before making a reviewed candidate or pending-review cache. The basis names each affected item/reason and returns null counts; private data is not converted to Certifications or dropped. Project category/organization/role/status/location and non-day date precision remain blocked where v1 cannot preserve their meaning. Codec v1's Wording/EditorialDelta contract accepts only text, boolean or null: list-valued additional-project links therefore block the complete review even while unselected, rather than being coerced to text or partially consumed. Package6 owns the required codec/complete-candidate extension; B2 does not expand contracts/schema or pretend that qualification.

Two new grouped cases were RED (6 failures), then the publication/draft/policy group passed **171/171 in0.511s**. They use actual local draft→primary canonical records, check named blockers for both qualification kinds and4 project field cases, unchanged pending review, unchanged private values and absent publication. Logs: `b2-codec-blockers-red.log`, `b2-codec-blockers-green.log`. The broader extra-field and complete-candidate limitations are explicit follow-ups, not a Pete-specific logic branch or a false complete-publishing claim.

Source B2 remains unfinished; visibility, references, all-path repairs and Guide GET integration plus final normal/concurrent/exact-review gates are still open. No accepted review receipt or deployment is inferred from these local checks.

The synthetic expiry probe `X:/PeerSlate/ChatGPT/evidence/mvp1-fixture-parentkey-2026-10-13/b2-policy-read-effects.json` finds one policy save through each of publication-candidate and first-arrival reads, changing an expired fictional deleted row to permanently deleted. The pending-review cache remains untouched, but durable read purity does not yet pass. Fix the existing policy projection with an explicit read-only path and update the existing canonical fixture after native custody; preserve legacy cleanup callers, owner isolation and shared publication authority. No real owner data, database, inference or installed site was used.

Jev checkpoint `b2-readonly-expiry-20261013`: the investigation compares a shared read-only policy path with duplicated downstream filtering; the reproduced save and actual call chain are relevant evidence and can change the implementation/regression focus. Free status `fcbdea15-d236-45a6-b633-f22f3d165f97` remains `usable_now=false`, `ongoing_paused_transport_failure`. Skip evaluation for that availability reason, preserve the existing policy rules, test expiry on copied state plus Guide/publication callers, and continue without retry or settings changes. The confirmed old write preflight governs this existing owned publication WIP; checkpoint it cleanly before the next native custody operation and fresh write preflight.

The ordinary two-file publication extension is accepted: PR1368/main **`7dff63651d4effd580266d9b641352b11d260524`**, required CI4584 succeeded2026-10-13T23:55:17.633837Z, claim bytes equal control candidate37aee415. The native control lease was released. Journal `fdf0feb18e914488607f021efd8e8d72a58c874f467482d0320dcabbb51baba5` imported that main and disjoint accepted D1 into the existing branch at **`63628546ffa7e68415391f08f7d89dc9d87c142a`**, retaining the exact bound plan/baseline/criteria and all prior runtime bytes. A fresh write preflight passed before B2 code began. These two surfaces now belong to B2 until the mandatory post-acceptance release; neither publication file has been changed in this first implementation checkpoint.

`GET /guide` and the owner working-set read expose one `first_arrival` descriptor: `read_state`, nullable `eligible`, and shown/dismissed/started flags. It uses the same owner intake snapshot plus actual private draft/My Data reads, with no save, provider call, default-count heuristic or inferred completion. Empty composer navigation/default blank fields and null text are not content; real unsent words, attachments, private draft items/media, saved items and Guide history are. Unsupported storage, malformed snapshots/receipts and unavailable canonical authority stay unknown. The qualified snapshot store retains the marker and receipt; the closed SQL mapper does not advertise this capability, and no SQL/schema/live-engine claim is made.

The existing owner Guide command seam accepts a closed `first_arrival_action` acknowledgment with its immutable UUID. Owner-lock serialization gives one fresh shown winner across two tabs; exact replay returns the original receipt but never a new `show_now` grant. Dismissed/started markers remain distinct from Guide completion and canonical content. Lost post-commit responses preserve the marker and replay safely. Unrelated stale whole-owner snapshots cannot erase these monotonic markers or their request receipts. Mixed status/client-owner payloads refuse; legacy member-status behavior is retained. C2 still owns automatic opening and must require a fresh `show_now` response, not merely eligibility or a replayed receipt.

Actual canonical-read-unavailable responses previously carried empty items; the shared canonical read now requires its explicit complete-read capability, so the working-set route returns unavailable instead of empty. A meaningful HTTP regression also caught welcome metadata changing the content token; first-arrival lifecycle is now excluded from that token, and the acknowledgment leaves the resume draft version and content token unchanged. Every new unit/HTTP seam was observed RED before its implementation; additional self-review cases cover the actual null/blank composer shape, malformed receipt and lost acknowledgment response.

Verification: **299 affected Guide/model/intake/runtime/routes/draft and fake SQL-contract/catalog regressions PASS in13.923s**; final **20 focused first-arrival/Guide HTTP tests PASS in0.029s**, including the subsequently added lost-response case and read-only draft/canonical/provider spies. Raw broad log: `X:/PeerSlate/ChatGPT/evidence/mvp1-fixture-parentkey-2026-10-13/b2-first-arrival-regressions.log`. All fake/$0; SQL agreement tests are not engine proof. Complete incremental source diff and whitespace self-review pass. The fixed8 criteria/baseline are unchanged and `checks` stays empty: the rest of B2, full retained-browser normal/load, independent exact-SHA review, candidate acceptance/CI/merge and the later two-file release remain outstanding.

Jev checkpoint B2-0 architecture/regression focus: relevant alternatives existed for persistence/read qualification and affected checks. Free status **`bafaa3a4-bd8a-4595-8cba-a562f5c5cb1c`** is unusable/paused for transport; no evaluation, retry, alternate gateway or allowance change. Fallback uses the existing qualified snapshot/owner-lock/receipt foundation, explicitly leaves SQL unsupported, and runs the changed privacy/read/command and declared SQL-agreement regressions. The corrected plan procedure itself is prescribed and deterministic. Claude's actual successionf3073ae supplies new reviewer `session:16023c0e-7189-420e-8a4d-11f8012a9713`; earlier9fb18 review receipts remain historical. Central'sb2dc36e notice records Dot's current stand-down; existing package authority and SM3 reporting continue, without routine Dot approval/polling.

An additional actual outage test was RED: an explicit dismissal/start unnecessarily required the catalog read needed only for automatic showing. Acknowledgment validation now separates those explicit member choices from the absent-content qualification, while shown still refuses unreadable authority. No completion or content save is inferred. The final **301 affected regressions PASS in14.083s**, including the lost-response and explicit-outage cases; log `X:/PeerSlate/ChatGPT/evidence/mvp1-fixture-parentkey-2026-10-13/b2-first-arrival-final-regressions.log`. B2-0 remains unreviewed source work within the unfinished B2 round.
# B2 visibility checkpoint — source only, not a review candidate

Private Hide/Show now records an explicit owner choice in the existing intake
receipt history. It creates no synthetic source or fact. Saved choices also
stamp the existing draft version atomically, preserving words, media, canonical
permissions and the public copy. Pending choices retain `state=pending`, their
identity/source/original values, and return to waiting on Show. Working-set and
item revisions fence new requests; exact receipt replay precedes stale checks.
The real HTTP route uses the same completed working-set token as its GET.

Three service cases first failed because the command did not exist, then passed.
193 related tests passed in 4.657s. The wider 256-test run found one old assertion
in `tests/test_resume_onboarding_conversation.py`: it expects the entire draft
workspace, including its version, to remain identical after restoration. The
new stale-publish requirement intentionally increments only that version; the
test needs the normal one-file surface extension before correction. The other
255 tests passed, including the real HTTP owner, same-origin, stale, replay and
waiting-restoration journey. Logs: `b2-visibility-regressions.txt` and
`b2-visibility-http-legacy.txt` in the fixed external evidence folder.

Jev checkpoint: the existing paused transport remains unusable; source-backed
atomicity and stale-preview regression checks were used, with no evaluation,
retry, model change or new authority. B2's eight criteria remain incomplete.

The Guide GET now consumes the publisher's single validated basis, supplying
the proven private inclusion history and filtering hidden descendants. Existing
sharing choices remain authoritative; Show never enables visitor AI. The route
returns per-item published/proposed membership, exact candidate/digest, change
count and blocked reasons, with unknown/null on unreadable or competing state.
The token used by Hide/Show is the actual completed GET token. A source purge
invalidates a hidden pending suggestion; Show on an already-shown item refuses.

The new real HTTP publication journey was RED for the absent basis, then GREEN:
a published role and Contact remain in display and visitor AI after private Hide,
both disappear only after explicit publication of this exact preview, and the
following GET reports zero changes. GET spies prove zero policy/draft/publication
saves. A competing draft writer produces unknown/null instead of a false count.
246 affected service/route/draft/publication tests PASS in12.181s, log
`b2-guide-publish-basis-regressions.txt`. The one wider legacy assertion still
awaits accepted one-file custody PR1372; no complete B2 acceptance is claimed.

PR1372 is now merged at `c76e5b0ddfe47cdf2a774f84af0fd8fb2af2d6ca`;
CI4600 succeeded at2026-10-14T06:04:45Z, with deployment/schema stages skipped.
Native reconciliation `ab51150517d15217d737160785e6e44f1d49aaaf23ac59b87f1458388dd956db`
imported that claim into source `00304a1903cd0d57e18d067e7c8f13bbfdeb3eea`.
The legacy assertion now compares every workspace field unchanged except the
required version increment. All362 related conversation/service/route/draft/
publication tests PASS in13.451s (`b2-visibility-complete-regressions.txt`).
The control lease is released. The app cannot attach Azure PR URLs; the actual
PR and CI evidence remain recorded here.

Fresh coordination pull8378ecc supplied actual Claude confirmationdbb8645:
all four overnight details and Contact mapping are confirmed; that request is
resolved. New implementation questions must go through Shared/handoffs while
Claude is active. The reported overnight production/8443/model/ask-first holds
remain. Jev statusf17a3834 is still paused for transport, so no evaluation is
permitted; remaining link/storage/selection questions use governing source and
Claude clarification. No retry or settings change was made.

## B2 Story binding and all-path text limits checkpoint

Explicit Save in the Guide's My Story section now designates the actual saved
personal entry through the existing `bind_story` command, in the same qualified
intake unit of work. The binding's child request is deterministic. Exact replay
does not create another entry or version; an injected binding failure restores
the canonical, draft and pending-proposal state. An ordinary personal-entry save
still does not silently designate My Story. The new success/rollback case was
RED twice before implementation;33 focused checks then passed.

The shared non-mutating text-limit helper now also guards existing manual draft
saves and primary knowledge writes for named Impact/Looking Ahead entries.
It preserves the supplied text and refuses over70 whitespace words or over120
UTF-16 units. Historical oversized selected entries get a named publication
blocker, with null counts; they are not truncated. Manual and primary bypass
cases were RED before correction; the historical publication case was also RED.
324 related editor/primary/draft/intake/conversation/publication checks PASS
in3.259s (`b2-story-all-path-limits.txt`).

The actual fake-model conversation retains an oversized summary pending with its
exact source. The real document parser/organizer path also retains a71-word
uploaded summary and its source unchanged after refusal; only the member's
explicit70-word edit saves. That additional import case PASSed in0.006s.
These are fake-provider/process-local checks, not live model or SQL proof.
Jev evidence/regression checkpoints use the recorded paused-transport fallback;
no inference or broader test programme was started. Remaining mapping questions
are in coordinationd7311e8; B2 is not yet a complete candidate.

## B2 reference resolution core — persistence awaits Claude mapping

The shared Guide projection module now resolves server-held skill and highlight
references against the already owner-bound working tree. Accomplishment links
follow the current private wording and actual parent employer/dates. Summary
references require the exact line digest; a changed line reports needs recheck.
Pending, hidden, absent, wrong-type and ambiguous-alias targets provide no
evidence. Hidden ancestors also filter their children. Show restores the same
stored references; no keyword matching or copied text is stored by this helper.
Only actual nonblank saved metric values make highlights; up to4 are shown in
the supplied order, and skills show up to3 resolved references.

Two meaningful cases were RED for the missing resolver, then GREEN with real
shared canonical/draft/intake stores: other-member data is absent; private edits
follow through; clearing a number removes its tile; Hide/Show preserves choices.
The digest and cap case also passes.124 affected Guide/projection/intake checks
PASS in4.543s (`b2-reference-resolution.txt`). Reference persistence, manual
precedence, command revision checks and codec handling await the actual answer
to d7311e8; this pure read helper is not the full `b2_links` acceptance.
These resolver behaviors are specified by ARCH §6h; no unresolved advisory
judgment replaced a required rule. Storage alternatives remain with Claude,
using Jev's recorded paused-transport fallback, without an inference call.

## B2 literal Project links stay out of model context

An actual fake-provider conversation was RED because saved Project URL fields
were included in its targets. The shared model-values projection now omits both
Project URL fields, and the conversation field contract does not offer model
editing/clearing of them. Their literal private values remain intact. Retained
structured input also keeps its URL privately without sending it in model
materials. That actual path exposed and corrected the missing Project subject
field in matching (`project_name`). No URL is fetched.

A real summary-revision test caught a false stale conflict after redaction:
the proposal had hashed redacted model values rather than the captured full
server values. It now retains the existing server-only canonical values digest;
changing summary works while the private URL is preserved, with no URL in the
provider context. The older wire-contract test explicitly excludes the ruled
private-only URL fields. Renaming an existing Impact entry also no longer
bypasses its limit on an older manual or proposal save path (RED then GREEN).

312 affected conversation/runtime/intake/Guide/draft checks PASS in5.994s
(`b2-project-context-final.txt`). No extractor-section vocabulary, provider call,
model selection, codec or schema was changed. These URL exclusions follow the
explicit269ab17 ruling, so the implementation is deterministic; Jev is still
paused and no inference was attempted. Fresh coordination pull3808458 has no
answer to the remaining mapping request yet; dependent storage/default work
remains pending while independent work continues.

## B2 reference command/storage checkpoint (narrow30-minute continuation)

After requestd7311e8 remained unanswered for about30 minutes, a fresh pull3808458
at06:38Z and the actual8378ecc rule allowed the narrow reference-storage detail
only. Same-note updateffdcdc8 records that scope. Empty-body essentials and new
display defaults remain strict/preserved while unanswered; this is not a blanket
provisional rule or product decision.

`POST /api/resume-intake/me/guide/references` records explicit manual choices in
the existing private draft: a skill item's `evidence_refs`/manual marker, and
root `highlight_refs`/manual marker. Owner-derived working-set tokens, current
record identities, exact summary digests and the atomic draft version fence
protect the command. Receipts classify exact replay before stale checks. The
unit of work rolls back metadata/version if its intake receipt fails. Reference
aliases bind to the actual saved record keys. Foreign, missing, pending, hidden
or wrong-type targets cannot supply evidence. SQL remains unsupported before
database calls, returning the retained proposed references.

Words, media, permissions and the public copy are unchanged. Later manual word
edits preserve accepted link choices. The Guide GET resolves those references
against current private records; malformed or competing metadata is unavailable
rather than an empty view. The complete v1 publication candidate is blocked
with `publication_codec_skill_references` / `publication_codec_highlight_references`,
including empty manual choices, so the current publisher cannot consume/drop
metadata it cannot carry. Package6 must support this before publishing it.

Hard canonical deletion prunes affected private references in the existing
policy/publication linked transaction, with the qualified private draft lock and
rollback. An injected publication failure restores all3 stores; exact deletion
replay causes no extra draft increment. Hide only filters references and does not
delete them. No public rendering or publication codec was extended.

The missing command/route, alias binding, hard-deletion cleanup, retained SQL
input and malformed-read cases were observed RED before correction. The real
HTTP route proves owner isolation, actual GET-token use, private/no-store, exact
replay and stale refusal without a fabricated application response.457 related
intake/routes/draft/publication/policy/Guide/conversation/runtime checks PASS
in15.031s (`b2-reference-storage-regressions.txt`); final11 reference/HTTP cases
PASS in2.165s (`b2-reference-storage-final.txt`). Jev remains pausedf17a3834;
source-required owner/identity/deletion checks and the recorded narrow fallback
were used, with no inference/retry. B2's fixed8 criteria are not yet all complete;
retained full-browser normal/load and exact-Claude review remain outstanding.

## Confirmed remaining Guide essentials (actual Claude answer 8eff4fc)

The actual fresh-pulled answer resolves d7311e8/ffdcdc8. Explicit qualified local Guide role requires role_title only (absent employer stays null); generic knowledge requires title only (absent wording stays null). Impact, bound My Story, Looking Ahead and Contact still require actual wording, with typed missing_required_fields and original pending input retained. Existing Contact/Story section requirements survive label renaming. Strict default editor/policy behavior remains unchanged. The actual shared catalog forwards explicit Guide options, and unqualified SQL refuses before storage effects.

A bounded external worker prepared a patch against exact 97b2e909 without product writes; this owning writer checked applicability, applied and reviewed it. Applied actual source:276 related tests PASS in4.733s (b2-final-mappings-applied.txt), including7 added regressions. Two earlier harness invocations were corrected (missing synthetic app environment, then a nonexistent test-module name); neither represented a source failure or passing verification. Absent-Guide normalized command comparisons are byte-identical in the worker evidence. This source checkpoint is not independent review or full B2 acceptance.

The newly saved proposed-display default remains a named unresolved implementation detail: durable historical publication evidence cannot distinguish explicit false/false exclusion from never-selected private items. No heuristic was applied. Question675f155 is published in Shared/handoffs/2026-10-14_codex-pc_to-claude-pc_B2-display-selection-provenance-question.md with the concrete gap and a bounded prospective provenance proposal. C1 work continues while Claude answers. The old remaining-mapping request itself is resolved. Package6 must carry refs/highlights/project arrays/qualification kind in its codec before package10; C3 must implement the real queued Send during organizing. No paid/model/config/schema/deploy/installed-root change. Jev paused f17a3834, no evaluation/retry.

### Direct Primary edit section fence

Writer self-review found that the newly explicit local Guide option could empty an existing named Contact/Impact/Looking Ahead/My Story through a direct Primary edit after renaming its label. All4 subcases were RED (b2-policy-rename-red.txt). The edit now derives an existing text-section requirement from the actual saved values before validating the proposed values; supplied new labels/sections cannot remove it. Draft-bound custom Story remains guarded by the draft's actual binding as already tested. Final277 related tests PASS in4.748s (b2-policy-rename-green.txt). No unqualified/default command or SQL contract changed. This is a correction of the same confirmed essentials requirement, not a new product choice.

## Prospective display-choice provenance (actual Claude answer6b9a5b7)

Fresh-pulled actual reply Shared/handoffs/2026-10-14_claude-pc_to-codex-pc_B2-display-selection-provenance-answer.md resolves question675f155. The existing qualified memory owner publication snapshot now records only whether a display choice has ever been made: never_selected at canonical create, explicitly_chosen on a display permission choice or explicit Publish of the complete reviewed list (including excluded false/false entries). Actual canonical flags retain the chosen values. The existing linked policy/publication transaction and integrated Publish transaction save/restore provenance atomically; no second store, schema or codec. Replays never rerun creation/choice effects.

Guide's read-only shared-candidate seam defaults display only for known never_selected new items, never grants visitor AI, and retains historical/unknown flags. It exposes unknown/unavailable provenance, validates metadata and rechecks the provenance snapshot as well as existing working/candidate fences. SQL provenance reading returns unsupported before touching storage; existing SQL choices stay unchanged. GET initializes nothing and creates no pending review.

Initial default probes were RED; final7 provenance tests cover proposed-only new inclusion, explicit false/false exclusion after reload/republish with unchanged access_revision1, historical unknown, create/permission replay, AI-independent permission choice, linked rollback, malformed metadata and SQL refusal. A pre-existing dynamic publication Mock needed its new optional provenance read explicitly set to unsupported (None); its fabricated default Mock value correctly failed closed. Final524 affected server/editor/draft/publication/routes/conversation/runtime tests PASS in15.959s (b2-display-provenance-regressions-final.txt). No full retained-browser, independent B2 review, source acceptance/merge, installation or production is claimed yet. Jev still paused; no evaluations/retries/provider/model/config/schema/credential changes. D6 codec and C3 queue dependencies remain required before package10.

### Outer Guide-confirm transaction and current browser frontier

Source121f09ea479bb9a9d8e4a1c0bbf66d5e75af1878 corrects a concrete outer-transaction gap: a canonical create's linked display-choice provenance survived when later Story binding or the final intake receipt failed. The new regression was RED in all4 combinations (binding/receipt failure, before/after an existing publication). Intake, draft and Primary snapshots were restored, but publication metadata retained the failed item's never_selected marker. The memory-only intake unit of work now qualifies and snapshots the existing publication participant, holds the publication lock before the draft lock to match Publish, and restores only touched owners on failure. ExitStack releases acquired locks even when snapshot entry fails. Unqualified publication storage refuses before writes; no SQL transaction/schema support is claimed.

Six focused essentials/atomicity checks PASS1.366s, including all4 rollback subcases, a controlled real Publish concurrent with failed Guide confirmation, preservation of that completed publish, unsupported-store refusal and cross-thread lock acquisition after a failed entry. The broader affected intake/runtime/routes/Guide/draft/publication/editor/conversation set passes521 tests in17.081s. Logs: X:/PeerSlate/ChatGPT/evidence/mvp1-fixture-parentkey-2026-10-13/b2-outer-provenance-{red,green,focused,regressions-final}.txt. Initial invocations used wrong unittest class/module names and one missing test import; those loader/test-setup failures were corrected and are not counted as runtime regression evidence. Complete incremental diff self-review and whitespace checks passed. A write-preflight invocation omitted its mandatory --require-clean flag and refused; the already-owned correction was committed/pushed normally, then a fresh complete clean/fetched write preflight passed at121f09ea. No branch/worktree/ownership bypass occurred.

At prior source64fc49e2, strict152 normal PASS285.971s and concurrent load2 PASS284.386s; load1 had one actual20-second Guide-opening timeout. Sixteen read-only focused reproductions passed without changing assertions/deadlines, and do not erase that failure. The historical failed page lacked HTTP/DOM/JavaScript evidence, so its cause is unknown; a controlled late-request/fixture-cleanup probe did not support that proposed cause. The external diagnostic strict wrapper retains actual152 selection, execute_suite semantics, deadlines and fail behavior, while capturing startup response/DOM/JavaScript evidence before re-raising. It neither retries nor skips a failed case. New source121f09ea still requires its final normal/concurrent152 proof, independent exact-SHA Claude review and fixed8-criterion acceptance/CI; no acceptance or delivery claim is made here. The mandatory later publication pair release, separate fixture return to C14 and retained-browser return to C1 remain tracked.

### Fixed Impact Statement error contract

At637a07cce612e39f8b5b69914fa82cd923145165, strict152 normal PASS269.081s and simultaneous152each PASS275.016s/279.295s, zero errors/failures/skips and no captured startup failure. Start/end metadata proves clean unchanged637a07cc for every copy. Logs b2-strict-final-{normal,load-1,load-2}.txt and b2-startup-final-{normal,load-1,load-2}-run-metadata.json remain historical proof for that source; no causal fix for the older startup timeout is claimed.

Mapping the fixed8criteria then caught one implementation discrepancy: b2_impact_cap explicitly requires impact_statement_too_long, while the new shared validator emitted impact_too_long. All existing service/HTTP/import/fake-model/publication limit assertions now require the fixed-plan name. Test-only patch first produced10 RED assertions across394 tests (b2-impact-contract-red.txt), with the actual shorter label visible in every failure. The one-line validator correction propagates the committed name through those existing paths without changing70words, actual_count, limit, original preservation or any save/publication decision. No client code consumes the old label. Final broader560 checks PASS is recorded in b2-impact-contract-green.txt. The fixed baseline/criteria/plan are unchanged; this corrects implementation to the plan. Prior full browser proof is retained as prior-source evidence, and this changed candidate gets fresh strict normal/concurrent proof before independent review. No protected review request or B2 receipt has yet been issued.

### Retained browser fence assertion, after accepted custody

The required152 run at7181 had151passes and one obsolete saved-record-restoration expectation: it compared the entire private workspace before/after an explicit inclusion change, including the draft revision that B2 must advance to invalidate an old Publish packet. The source behavior was correct; the test file was C1-owned. Native unchanged-file C1 release PR1374 merged d527f194 after CI4607, then B2 exact-file extension PR1375 merged234220a7c9d43f4d42e5be5fbbbe6476dd0a6727 after CI4609 succeeded2026-10-14T09:24:26Z. No test or deadline changed in either control PR; no deployment/schema stage ran.

B2 journal86bf1d4e4de4ede35a3abc4ffda467ca16104fa20a799fb8426ccac0e9ff73be imported that main at275cd2ded7dce3e2d3df88c3d3539ae9cb8d1a50. The complete claimed-runtime byte comparison against7181 returned0. Fresh write preflight passes. The browser test now asserts exactly draft_version+1 and exact equality of every other workspace field; no runner, skip or timeout changed. Role and bullet restoration2/2 PASS2.380s (b2-retained-stamp-applied-green.txt), after the actual failed full run and an external prepared correction1PASS1.761. Required fresh152 normal/concurrent proof and exact-Claude B2 review are next. The fixed8criteria/plan/baseline are unchanged. Test custody returns after accepted B2, separately from mandatory publisher two-file release to D6 and fixture return to C14. No production/install/8443/model/paid/config/schema/credential change.

### Owner-requested paused handoff: unfinished review corrections

Pete explicitly requested on2026-10-14: "find a spot to pause and give me a handoff for Claude to finish this, to finish everything." Codex implementation is now quiescent for that transfer; the reused external worker is also stopped. This is a recoverable work checkpoint, NOT a reviewed B2 candidate or acceptance claim. The fixed8criteria/plan/baseline are unchanged and existing receipts still refer to historical B1 only.

Actual Claude review68e0942 FAIL at21d1eb6381135297e393669f4028b6ca6d3bca76, lock directione73a267, and early source-ack approval96c4fd1 were pulled/read in full. Unfinished correction source adds one common per-owner intake/publication/draft guard, request serialization, owner-bound memory UOW rollback, unlocked preparation plus revision-fenced apply for legacy submit and existing organize_source, and applies the external credential-year/published-order patchf17814f8. No new source-only mode or C1 receipt integration is implemented yet. Store/provenance and all SQL qualification boundaries remain to be independently checked against the corrected source.

Meaningful M2 deadlock regression RED at21 (b2-m2-regression-red.txt); the stronger pre-release-read regression also RED with ordering-only correction (b2-m1-unlocked-read-red.txt). After provider separation,6 focused concurrency/atomicity/byte-idempotency checks PASS1.363s (b2-m1-unlocked-read-first-green.txt). The latest combined7-module run (b2-m1-m3-m4-related.txt) ran381 checks in16.358s:2FAIL,0 unittest errors/skips. Both failures are existing BarrierDraftStore tests that block inside load_owner waiting for a second same-owner load, now serialized by the shared guard; their spawned threads raise BrokenBarrierError. Their assertions must be preserved while moving the test-start rendezvous before the guarded service call. No deadline increase/waiver is authorized. This is a known unfinished harness adaptation, not a passing broad run.

Whole-surface matrix is an unvalidated external draft b2_m1_concurrency_matrix_tests.py, with no syntax/run/patch proof. Exact-file M2 extension for tests/test_my_data_intake_ai.py remains undone. The Minor codec-blocked review route needs actual named blocked_items and its exact-file scope extension; dependencies for package5/6 and C2 still need recording. Fresh full strict152 normal/concurrent tests, acquisition-order audit, exact-SHA independent review, native evidence mapping/current-target CI/merge, publisher-pair release to D6, fixture return to C14 and retained browser-test return to C1 all remain required. No product deployment,8443stop,paid/model/credential/schema/installed change. Jev skipped: prior observed paused transportf17a3834 remains the recorded unavailable connection; the pause/transfer is Pete's explicit direction, not an unresolved advisory choice.

### Review-1 corrections completed by the Claude writer (B2 round 2 candidate)

Custody: Codex relinquished at `2f46d47132913bba385e4327a3954f53b6b3dc9b`. Transfer PR1377 merged `74e3b22b`; exact-file extensions PR1380 and PR1381 added `tests/test_resume_intake_sql.py` plus `tests/test_my_data_intake_ai.py`, `resume_publication_routes.py`, `tests/test_resume_publication_routes.py` and `services/resume_publication_contracts.py`. The writer is `agent:claude/2026-10-14/guide-build`. Independent reviewer: the Claude manager `session:16023c0e-7189-420e-8a4d-11f8012a9713`, on Pete's direct 2026-10-14 routing. The fixed 8 criteria, plan and baseline are unchanged.

Fake providers only, 0 paid calls. External evidence root: `X:/PeerSlate/Claude/reviews/b2-builder-evidence/`.

**M1, locking (rule e73a267).**
- **Codex's provider separation is kept:**
  - no owner or store lock is held across any provider call;
  - per-owner `resume_owner_guard`, in the order intake → publication → draft;
  - snapshot, then unlocked dispatch, then fenced apply.
- **The read-only audit found three more same-class defects in the in-memory composition**, which the local private sites use through `tests/mvp1_acceptance_support.py`:
  1. Publish held the draft store lock and then took the bound-media lock, while every media read takes bound media and then the draft store: a cross-owner ABBA.
  2. The Guide unit of work held the draft store lock and then took the media lifecycle lock through the publish basis, while media commands and Publish take lifecycle and then the draft store: a cross-owner ABBA.
  3. Recording finalization, recording claims, composer-draft CAS, entry-policy expiry writes and `bind_slug` wrote owner state without the owner guard: lost updates.
- **Correction, at one choke point:** `ResumePublicationService._memory_media_locks()` takes media lifecycle, then bound media. Publish and `InMemoryIntakeUnitOfWork._enter` both take it before the draft store. The global in-memory order is now: owner guard → media service → media lifecycle → bound media → draft store → intake store. The listed writers now take the owner guard first.
- **Proof:**
  - The integrated whole-surface matrix (Codex fragment `ca33d824…`, used unchanged) passes 8/8, and has 16 failures at `21d1eb63`.
  - Three new store-order regressions park a second owner's real command at the exact earlier-lock point. They pass 3/3 with the fix, and all 3 fail without it (two deadlocks and one lost-update wait).
  - The ranked lock-order witness harness (`lock_order_witness.py`, evidence only) wraps every in-memory owner and store lock across 19 affected modules (812 tests). Before the fix: 1 violation, draft store → bound media at publish. After: 0 violations, 0 failures.
- The two `BarrierDraftStore` cases now meet at a start rendezvous before the guarded call. Their assertions and deadlines are unchanged: RED 2/2 at `2f46`, GREEN now.

**M2.** The extraction vocabulary is unchanged. The contract test now asserts the ruled divergence exactly: editor-only `project` and `credential.qualification_kind` are absent from extraction, and everything else is equal. It is RED at `2f46` and GREEN now.

`test_unreadable_catalog_fails_closed` had counted workspace reads ("fail after the first"), and the new processing fence shifted that count. That was a new deterministic failure at `2f46`. The gate now fails exactly the matching-shortlist read, and the assertions are unchanged: the result is `inferred_wording` with no target. A mutation check that disables the gate makes it fail with `additional_detail`, so the test still proves fail-closed on the read that matters.

**M3 and M4.** These are Codex's applied corrections from patch `f17814f8`, unchanged and re-run in the focused suites.

**m1.** `ValidationResult` gains `blocked_items` (refs and reasons only, never content). The review route's codec 409 names each blocked item. The new route regression is RED at `2f46` (`KeyError: blocked_items`) and GREEN now; the pending review stays empty and nothing is published.

**m2 and m3 dependencies (recorded, not changed).**
- Package 5/6 "Publish changes" must read only the Guide publish basis, so a private Hide is respected (f2f91cf §5). The existing publication page's explicit review still proposes from canonical flags, and nothing publishes silently.
- Any `highlight_refs` key, including an empty manually cleared list, makes Guide publish status unavailable until D6 lands codec support, consistent with 8eff4fc. C2 copy and package 6 must say so honestly. The optional empty-list relaxation is not selected.

**Next, separately planned:** the C1 M3 source-only receipt (96c4fd1). On the reviewer's choice (a), it is a follow-on server increment with its own committed plan, merged before C1.
**Runs (fake providers, 0 paid, process-local CI placeholder key; scratch exports byte-identical to the candidate's runtime and test files):**
- Focused: 19 affected modules, 812 tests, 0 failures/errors, run under the lock-order witness (0 violations), `witness-after-lock-fix-812.txt`. `tests.test_resume_intake_sql` 46/46 with its corrected replay test.
- Strict browser: 152/152 normal in 319 s; two concurrent copies 152/152 each in 312 s; 0 failures, errors or skips; runner unchanged (`strict152-*.txt`).
- Full no-Playwright discover:
  - base main `f258615a` (claim-only difference from `8847dd2c`): 7705 run, 303 skipped, 16 errors, 19 failures;
  - candidate: 7821 run, 303 skipped, 16 errors, 20 failures;
  - the only candidate-only entry was the SQL replay test, corrected after that run and passing in isolation and in its module, at both `21d1eb63` and the candidate;
  - every other entry is identical to base, including the known local-only `test_ephemeral_invocation_lease_blocks_concurrent_retirement` and the PDF second-column case, which also fails at `21d1eb63`.

### Round-2 review corrections (N1–N3)

Reviewer `16023c0e` reviewed round 2 at `3b775498` (coordination `4bedbba`): every round-1 finding is resolved; N1 Medium must be fixed before merge; N2 and N3 are Minor. Evidence root: `X:/PeerSlate/Claude/reviews/b2-builder-evidence/round3/`.

- **N1, narrow processing fence.**
  - `_processing_fence` now digests only what a prepared result depends on:
    - the lifecycle epoch;
    - the exact source rows it reads (referenced recordings for submit, the organized source for `organize_source`);
    - the proposals already bound to those sources.
  - The new `_check_dependent_targets` compares every saved item a prepared draft references (`match_reference`, `parent_reference`) with the exact shortlist entry the provider saw. A changed, deleted or newly excluded target reports `changed`, with the input kept and nothing forced. `organize_source` records its dispatch result so the same check covers it.
  - The draft workspace, Hide/Show, references, Publish, publication revision and unrelated proposals are no longer fenced.
  - **Tests:** `ProcessingFenceScopeTests` holds the real provider in both submit and `organize_source` modes.
    - Hide-then-Show, a references save, Publish, an unrelated proposal decision and an unrelated edit each let the paid result apply. All 10 subcases are GREEN and RED at `3b775498`.
    - A canonical edit of the matched target reports stale, creates no proposal, keeps the upload input or the source, and keeps the member's edit. Disabling only the dependent-target check makes it fail.
  - The matrix row with an unrelated canonical create now expects the result to apply. The purge row still refuses.
- **N2, store-level race kept covered.** `LoadBarrierDraftStore` has two callers load before either saves. They drive the undecorated `ResumeDraftService.commit.__wrapped__` (no owner guard), so only the store's receipt check inside `commit_owner_command` can converge them: an identical body replays and a changed body is `idempotency_conflict`. Disabling that store check fails both tests. The service-level pair is kept.
- **N3, recorded as observed, not reproduced.** In the reviewer's first two-copy strict run, copy 2 had one load-timing error in `test_failed_correction_then_manual_confirmation_preserves_newer_words_and_allows_next_correction` (`wait_for` on the private-assistance-unavailable text). The run completed, the test passed 5/5 in isolation and in the reviewer's second pair, and it was not seen in this writer's runs. There is no retry, retiming or runner change. One more two-copy strict-152 run on the new SHA is below.

**Round-3 runs (fake providers, 0 paid; scratch export byte-identical to the candidate's runtime and test files):**
- Focused: 21 affected modules, 877 tests, 0 failures/errors, under the lock-order witness with 0 violations (`r3-witness.txt`).
- Strict browser, two concurrent copies: 152/152 each in 308 s, 0 failures/errors/skips, runner unchanged (`r3-strict-load*.txt`).
- Full no-Playwright discover: 7825 run, 303 skipped, 16 errors, 19 failures, with a failure set identical to base main `f258615a` (`r3-discover.txt`).


### Current-target CI finding on PR1382 (reported, not rerun)

Build 4629 (merge `4fa9d188` of the receipt tail on `5730a316`) ran strict 152 at 151/152. The one failure was `test_finish_without_unsent_input_has_no_false_reminder`, which asserts at `tests/test_resume_intake_browser.py:1924` that no unsent reminder shows; every other required job passed.

The cause is a race in the test harness, not a product fault:
- `finish_input()` checks once whether `#resume-intake-input-finish` is visible;
- under load the question renders before that button;
- the helper then types an answer;
- the finish screen truthfully reports that answer as unsent.

The writer reported it instead of rerunning, and the reviewer approved option (a): in that test only, wait for the button to be visible before `finish_input`. There is no retry, deadline, helper or runner change, and the assertion is unchanged. Locally the test passes 3/3 and its module passes. This is a new candidate for a delta recheck plus one current-target CI run.

Read-only sweep of the other `finish_input` callers:
- `:1900` (explicit private finish) asserts the publish wording, completed status and an empty catalog;
- `:2174` (lost completion) asserts the finish screen and the identical completion calls;
- `:2410` and `:2514` (Story destination) continue into Add story;
- `:2737` and `:2744` type input deliberately first.

None of them asserts the absence of typed or unsent input, so none carries the same false-assertion risk. A named C1 follow-up is recorded for when this file returns to C1: replace the helper's instantaneous visibility check with an explicit precondition at each caller.

## B2b pre-code round plan (v2): source-only receipt and bounded request guard

_Plan v2 supersedes plan v1 `4c7c81dc` before any B2b code was committed. On the reviewer's direction, the busy result uses the retryable 503 shape today's intake client already keeps the request id for; the v1 409 shape would have made today's client retry under a new id._

**Outcome.** B2 was accepted and merged: PR1382, main `1107ca695aa14b5c19fbcd8e260e7d2ab5088264`, CI 4633 green, independent PASS at `492b2643`. The B2 acceptance JSON above is kept as historical JSON and is no longer the active record. B2b is a small follow-on server increment under the same claim. The reviewer chose it (option a) to merge before C1.

**Scope (manager rulings 96c4fd1 and the B2 review follow-ups):**

1. **C1 M3 opt-in source-only first document receipt.**
   - An initial document send with `source_only: true` commits the existing private original, source, reader and job foundation with zero organizer dispatch.
   - It is owner-qualified, replay-safe and atomic.
   - The existing `organize_source` owner command follows.
   - Legacy requests and their digests are unchanged when the opt-in is absent.
   - Unsupported compositions (SQL, or no organizer) refuse before any read or write, with the input kept.
2. **The required bounded request-guard acquire** for the bounded local private-site pool (waitress, `WORKER_THREADS = 4`, `tools/local_reviewer/runtime.py`).
   - An identical in-flight request waits only a bounded time.
   - It then returns the existing retryable unavailable shape the intake routes already use: `ResumeIntakeUnavailableError` (a typed `ResumeIntakeBusyError` subclass), rendered by the submission/organize routes as HTTP 503 with `proposed_values` and `input_preserved`. The typed body adds `code: request_in_progress`, `request_id` and `retryable: true`. Today's client keeps and retries the same request id on 503 (pendingAdd and pendingOrganize), so the retry replays.
   - An unrelated request must still complete while duplicates wait.
3. **R3-m1:** a test that fails if the source component of the processing fence is removed.

**Excluded:** client integration (C1), B3 conversation and conversion work, any model or provider change, schema, deployment and production. The organize request occupying one bounded worker during its provider call is a pre-existing C14 acceptance item, recorded there.

**Holds:** fake providers only and $0; no production, 8443 stop, model switch, credentials or schema. Independent exact-SHA review by `session:16023c0e-7189-420e-8a4d-11f8012a9713`.

```package-acceptance-json
{
  "schema_version": 1,
  "package": "PS-GUIDE-SERVER-001",
  "plan_sha": "c8cd0fc5414009580d16b91e2c5435b96e91758c",
  "candidate_sha": "9695f8d123b40b536016545d35ba27fb085ab58d",
  "baseline": [
    {
      "command": "X:/PeerSlate/runtimes/development/Scripts/python.exe -B -m unittest tests.test_resume_intake_service tests.test_resume_intake_sql tests.test_resume_intake_routes -q",
      "exit_code": 0,
      "observation": "211/211 PASS in 13.963s at accepted B2 main 1107ca69 before B2b code. Process-local CI placeholder key and fake/in-memory providers only. Raw log X:/PeerSlate/Claude/reviews/b2b-source-only-evidence/b2b-precode-baseline.log."
    }
  ],
  "criteria": [
    {
      "id": "b2b_source_only_receipt",
      "expected": "An opt-in source_only initial send of exactly one document stores and reads it as a private active source with zero organizer dispatch, no proposals and no canonical write, returns a truthful saved-file receipt that replays, and the existing organize_source then organizes it once. Absent or false opt-in keeps legacy behaviour and digest; switching a request id between modes is an idempotency conflict; malformed or mixed opt-in refuses before effects; SQL or no-organizer compositions refuse before any read or write with input kept.",
      "verification": "Service tests for receipt, replay, organize follow-on and repeat refusal, legacy digest equality, mode-switch conflict, malformed/mixed refusal with empty stores, no-organizer refusal and a SQL simulator refusal with zero procedure calls; RED on the B2 main tree; focused regressions and the lock-order witness green."
    },
    {
      "id": "b2b_request_guard_bounded",
      "expected": "An identical in-flight submit or organize waits a bounded time on the request guard, then returns the existing retryable intake unavailable shape (HTTP 503, typed code request_in_progress, retryable, input preserved, request id echoed) instead of occupying a bounded worker indefinitely; an unrelated request completes while the duplicates wait; the held request still finishes, and today's intake client retries the busy reply with the same request id so the server replays rather than dispatching twice.",
      "verification": "A held fake provider plus at least four same-request-id duplicates through a four-thread bounded waitress-style server while an unrelated GET completes within its deadline; duplicates return 503 request_in_progress with input kept; after release the original receipt replays; RED without the bounded acquire. A Playwright test through today's intake client (Guide rebuild off): a busy reply followed by the member's retry reuses the same request id and replays with the document read once; RED with a 409 busy shape."
    },
    {
      "id": "b2b_fence_source_component",
      "expected": "A test proves the processing fence's source component: changing the organized source's own row (or its bound proposals) during organizing refuses the stale prepared result while unrelated work still applies.",
      "verification": "Mutation check: removing the source component from _processing_fence makes the new test fail; existing ProcessingFenceScopeTests stay green."
    },
    {
      "id": "b2b_regression_review",
      "expected": "Affected server suites, strict 152 normal and two-copy load and full no-Playwright discover show no new failure against base; the exact candidate receives independent PASS; current-target CI and merge remain separate gates.",
      "verification": "Focused suites under the lock-order witness, strict 152 runs, discover comparison against main, exact-SHA independent receipt, package_acceptance check and merge preflight."
    }
  ],
  "checks": [
    {
      "criterion_id": "b2b_source_only_receipt",
      "result": "pass",
      "kind": "automated",
      "candidate_sha": "9695f8d123b40b536016545d35ba27fb085ab58d",
      "source_ref": "coordination:e3450da:Shared/handoffs/2026-10-14_claude-pc_to-claude-pc_REVIEW_PS-GUIDE-SERVER-001_B2b.md + tests.test_resume_intake_service.SourceOnlyReceiptTests + tests.test_resume_intake_sql + X:/PeerSlate/Claude/reviews/b2b-source-only-evidence/b2b-red-on-3b775498.txt",
      "observed": "One opted-in document is stored and read as a private not_started source with zero organizer dispatch, replays, then organize_source dispatches once; legacy digest unchanged; mode switch conflicts; malformed/mixed/no-organizer/SQL refuse before effects with input kept; RED at 3b775498."
    },
    {
      "criterion_id": "b2b_request_guard_bounded",
      "result": "pass",
      "kind": "automated",
      "candidate_sha": "9695f8d123b40b536016545d35ba27fb085ab58d",
      "source_ref": "coordination:e3450da:Shared/handoffs/2026-10-14_claude-pc_to-claude-pc_REVIEW_PS-GUIDE-SERVER-001_B2b.md + tests.test_resume_intake_routes.BoundedWorkerPoolHttpTests + tests.test_resume_intake_routes.LegacyClientBusyRetryBrowserTests + tests.test_resume_intake_service.ProcessingFenceScopeTests + X:/PeerSlate/Claude/reviews/b2b-source-only-evidence/guard-red-without-bounded-acquire.txt + X:/PeerSlate/Claude/reviews/b2b-source-only-evidence/legacy-409-red.txt + X:/PeerSlate/Claude/reviews/b2b-source-only-evidence/single-flight-red.txt",
      "observed": "Duplicates wait at most 2 s then get the retryable 503 request_in_progress with input kept; an unrelated GET completes on a 4-worker pool; today's client retries with the same id and replays (document read once); one organize per owner and source, so two tabs make one dispatch; each RED without its change."
    },
    {
      "criterion_id": "b2b_fence_source_component",
      "result": "pass",
      "kind": "automated",
      "candidate_sha": "9695f8d123b40b536016545d35ba27fb085ab58d",
      "source_ref": "coordination:e3450da:Shared/handoffs/2026-10-14_claude-pc_to-claude-pc_REVIEW_PS-GUIDE-SERVER-001_B2b.md + tests.test_resume_intake_service.ProcessingFenceScopeTests.test_a_change_to_the_organized_source_row_during_organizing_refuses_the_stale_result + X:/PeerSlate/Claude/reviews/b2b-source-only-evidence/fence-source-component-mutation-red.txt",
      "observed": "A source-row-only change during a held organize refuses the stale result as changed; removing the fence source component makes the test fail."
    },
    {
      "criterion_id": "b2b_regression_review",
      "result": "pass",
      "kind": "automated",
      "candidate_sha": "9695f8d123b40b536016545d35ba27fb085ab58d",
      "source_ref": "coordination:e3450da:Shared/handoffs/2026-10-14_claude-pc_to-claude-pc_REVIEW_PS-GUIDE-SERVER-001_B2b.md + X:/PeerSlate/Claude/reviews/b2b-source-only-evidence/single-flight-witness-888.txt + X:/PeerSlate/Claude/reviews/b2b-source-only-evidence/v2-strict-load1.txt + X:/PeerSlate/Claude/reviews/b2b-source-only-evidence/v2-discover-cand.txt",
      "observed": "Independent exact-SHA PASS at 9695f8d1; witness 888 tests with 0 lock-order violations; strict 152 normal and two-copy load pass; full no-Playwright discover failure set identical to base main."
    }
  ]
}
```

### B2b implementation evidence (candidate for independent review)

Fake providers only, $0. Evidence root: `X:/PeerSlate/Claude/reviews/b2b-source-only-evidence/`.

- **Source-only receipt.**
  - Opt-in `source_only: true` with exactly one document stores and reads it as a private active source.
  - The organization state is `not_started`, with 0 organizer dispatches, no proposals and no canonical write. The message reads "Your file is saved privately. Organizing comes next."
  - Replay works. Then `organize_source` (`retry`) dispatches once, and a repeat is `already_organized`.
  - Absent or false opt-in keeps the legacy digest. Switching modes on one request id is `idempotency_conflict`.
  - Malformed or mixed requests refuse with empty stores. A composition without an organizer is unavailable with input kept. The SQL simulator refuses with 0 procedure calls.
  - `SourceOnlyReceiptTests` plus the SQL test: 8 RED at `3b775498` (`b2b-red-on-3b775498.txt`), GREEN now.
- **Bounded request guard.**
  - `resume_request_guard` waits at most `REQUEST_GUARD_WAIT_SECONDS = 2.0`, then raises `ResumeRequestInProgress`.
  - Submit and organize surface it as `ResumeIntakeBusyError`, a `ResumeIntakeUnavailableError` subclass, through the existing 503 helper. The body carries `code: request_in_progress`, `retryable: true`, the `request_id` echoed, `proposed_values` and `input_preserved`.
  - `BoundedWorkerPoolHttpTests` uses a held provider plus 4 duplicates on a 4-worker pool server. The unrelated GET completes, the duplicates get the busy 503, and the held request finishes and replays. It is RED without the bounded acquire: the unrelated GET times out (`guard-red-without-bounded-acquire.txt`).
  - `LegacyClientBusyRetryBrowserTests` drives today's intake client (Guide rebuild off) through Playwright. A busy reply, then the member's retry, reuses the same request id and replays, with the document read once. It is RED with the plan-v1 409 shape (`legacy-409-red.txt`). This test is skipped in no-Playwright discover, and no CI browser job module list includes it; it is local proof.
- **R3-m1 fence source component.** `test_a_change_to_the_organized_source_row_during_organizing_refuses_the_stale_result` changes only the organized source row during a held organize and gets `changed`. Removing the fence's source component makes it fail (`fence-source-component-mutation-red.txt`). A purge is also caught by the epoch component, so it is not the sole witness.
- **Runs.**
  - Witness over 21 modules: 886 tests, 0 failures, 0 lock-order violations.
  - Strict 152: normal 152/152 in 317 s; two concurrent copies 152/152 each in 298 s.
  - Full no-Playwright discover: candidate 7834 run / 304 skipped / 16 errors / 19 failures; base main `cf9a31c5` 7825 / 303 / 16 / 19. The failure sets are identical, and the extra skip is the new browser test.

### B2b delta: one organize per source (reviewer-approved option a)

A reload or a second tab could send a second `organize_source` under a new request id for the same file, so the paid organize could run twice. The organize guard is now keyed by owner plus `organize_source:<source_key>`, with the same 2 s bounded wait and the same retryable 503 `request_in_progress` reply. Eligibility (already organized) and replay are re-read inside the guard, before any dispatch. An identical request id still replays after completion.

Tests:
- **One source, two request ids, provider held:** checked for both an unavailable source ("Try organizing again" in two tabs) and a source-only `not_started` source. Exactly one dispatch; the second request gets the busy 503 and then `already_organized`. RED without the change (`single-flight-red.txt`).
- **Two different sources of one owner:** both dispatch independently. This test is a no-regression guard and passes on both versions.
- **Runs:** witness 888/888 with 0 lock-order violations; strict 152 normal 152/152.
