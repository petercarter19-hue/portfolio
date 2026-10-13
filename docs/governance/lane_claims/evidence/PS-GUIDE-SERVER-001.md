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

```package-acceptance-json
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
