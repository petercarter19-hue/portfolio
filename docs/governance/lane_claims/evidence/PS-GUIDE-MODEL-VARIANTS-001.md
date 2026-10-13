# Guide model variants: acceptance and execution record

**Goal:** fixed named Guide variant records and the narrow owner-only Sol 6.1 request matrix, preserving incumbent behavior.

**Authority:** Pete's MVP1 build assignment; writer `session:01a132fe-1f81-77f3-8821-d53d157ca025`, Claude PC `local_4fefa9f6` independent exact-SHA reviewer. Activation PR 1355 merged at `5378590f6fd8e33c97fe6fd86973ad80d56be785`. Production and paid provider calls remain withheld in this implementation pass.

**Spec:** build plan v2, design rationale (including section 6), ARCHITECTURE section 6's fixed variant table and negative matrix, and EVALUATION_CONTRACT. Product Sol 6.1 medium is provisional and separate from this build chat's xhigh effort. No model selection is globally changed.

**Architecture:** immutable named records in `services/ai_foundation/contracts.py` describe model/deployment/version, owner purpose, effort, wire/token bounds and safety prices. The StructuredRequest field set and all incumbent defaults stay unchanged. Expose deterministic lookup/request/binding validation for package 3's existing server providers and package 1's pinned local factory/allocation. Their composition work remains in those packages; this package creates no second adapter, store, ledger or provider.

**Tech stack:** existing Python frozen dataclasses, immutable mapping, unittest and fake Azure Foundry transport.

## Constraints and review focus

- New combinations only: Sol 6.1 owner My Data extraction and owner Resume career interview, effort low/medium. Synthesis stays Sol 6.1 high only. Non-owner, matching, wrong product and other efforts are refused.
- Variant names: `turn.sol6_low`, `turn.sol61_medium`, `turn.sol61_low`, `organize.luna_low`, `organize.sol61_medium`, `organize.sol61_low`.
- Sol 6.1 model/deployment/version: `gpt-6.1-sol` / `peerslate-resume-sol61` / `2026-09-29`. Turn bounds 65536 bytes, 66560 input tokens, 16384 output tokens; organize bounds 73728 bytes, 74752 input tokens, 24576 output tokens. Safety rates 100000000 microUSD per million input/output tokens. Exact reservations are 8294400 and 9932800 microUSD, not rounded prose estimates.
- Incumbent records retain their existing deployment/version/envelopes/prices. No `variant` field is added to StructuredRequest, so absent-variant serialization cannot acquire an extra null field.
- Different record names, profile types, requests, deployment/version, settings/factory/allocation bindings or safety envelopes fail closed before credentials/HTTP. No record may be edited in place.
- Review focus: non-owner escalation; synthesis accidentally inheriting medium; wrong profile name despite compatible model; mismatched version/deployment/prices/envelope; accidental incumbent byte changes.
- All tests are fake/$0. Broadening the server adapter gate and its missing-model rejection belongs to package 3; allocation/factory digest changes belong to package 1. No paid functional proof or permanent product-model adoption is claimed here.

## Execution plan

Native execution in this chat, negative tests before code, Claude's required independent review and no extra Codex final-review layer.

- [ ] **Negative matrix and incumbent bytes.** Add `tests/ai_foundation/test_guide_model_variants.py` and extend existing foundation tests only as needed. Observe today's intended Sol 6.1 extraction/interview failures, preserve all rejected combinations, freeze canonical incumbent request/wire bytes and prove no credential/HTTP access on rejection.
- [ ] **Named records and narrow request matrix.** In `contracts.py`, add frozen records, immutable lookup by name/profile and deterministic request/settings/factory/allocation binding validation. Widen only the approved owner purpose/effort pairs. Keep synthesis high, existing dataclass fields/defaults, price classes and Azure provider source unchanged. Test all six exact records, unknown/malformed names, wrong profile and immutable/copy-safe behavior.
- [ ] **Verify, freeze and review.** Run focused foundation plus affected request/runtime regressions, inspect the complete owned diff, push an exact candidate and send branch/SHA/change/tests/acceptance to Claude via `Shared/handoffs`. Correct findings, add the fixed receipt/evidence tail, run acceptance/merge preflights and current-target Azure CI, then merge accepted work. Publish the consumer contract to packages 1 and 3 in this chat; permanent model adoption remains a separate evaluated decision.

## Acceptance plan (committed before code)

Pre-change command ran against the unchanged foundation blobs in `X:/PeerSlate/portfolio`; fetched main's intervening changes are claim-only. Result: 57 tests PASS, 0.329 seconds, fake transport and no provider calls.

```package-acceptance-json
{
  "schema_version": 1,
  "package": "PS-GUIDE-MODEL-VARIANTS-001",
  "plan_sha": "ea9ce05385f07ac79a2febdb88fc65c43323059f",
  "baseline": [{"command":"X:\\PeerSlate\\runtimes\\development\\Scripts\\python.exe -B -m unittest tests.ai_foundation.test_azure_foundry_provider -q","exit_code":0,"observation":"57 pre-change foundation tests PASS in 0.329 seconds, fake transport, no paid calls."}],
  "criteria": [
    {"id":"closed_request_matrix","expected":"Only the approved Sol 6.1 owner extraction/interview low/medium pairs are added; synthesis remains high-only and wrong purposes/products/audiences/efforts fail before provider work.","verification":"Exhaustive focused positive/negative matrix and no-credential/no-HTTP assertions."},
    {"id":"immutable_named_records","expected":"All six named records retain exact pinned model/deployment/version/effort/envelopes/prices/reservations; unknown names and wrong profile types fail and records cannot be mutated.","verification":"Exact record table, immutability and malformed-name/profile tests."},
    {"id":"binding_validation","expected":"A variant that disagrees with the request, server settings, factory contract or allocation is rejected before token/HTTP work, including deployment/version/scope/price/bound mismatches.","verification":"One-field tampering tests against real deterministic validators and fake provider admission."},
    {"id":"incumbent_byte_identity","expected":"No-variant incumbent StructuredRequest fields/defaults, complete wire payloads and envelopes are byte-identical to their pre-change snapshots; no global model switch or extra dataclass field is introduced.","verification":"Pre-change golden byte hashes and existing foundation/runtime regressions."},
    {"id":"review_and_delivery","expected":"Focused regressions pass and Claude independently passes the exact pushed candidate before ordinary accepted Azure merge; server/local consumer boundaries and missing real-model proof are explicit.","verification":"Exact-SHA review receipt, acceptance mapping, merge preflight and current-target Azure CI."}
  ],
  "candidate_sha": "de574fdea3a436e98a472320ab532b6ec53875ae",
  "checks": [
    {"criterion_id":"closed_request_matrix","result":"pass","kind":"automated","candidate_sha":"de574fdea3a436e98a472320ab532b6ec53875ae","source_ref":"X:/PeerSlate/coordination/codex-pc-mvp1-build/Shared/handoffs/2026-10-13_claude-pc_to-codex-pc_REVIEW_PS-GUIDE-MODEL-VARIANTS-001_round1.md:30","observed":"Independent exhaustive base/candidate matrix added exactly four approved owner pairs and removed zero; every other combination was refused with ValueError. Refusal is at StructuredRequest construction before any provider object exists, rather than an asserted transport callback count."},
    {"criterion_id":"immutable_named_records","result":"pass","kind":"automated","candidate_sha":"de574fdea3a436e98a472320ab532b6ec53875ae","source_ref":"X:/PeerSlate/coordination/codex-pc-mvp1-build/Shared/handoffs/2026-10-13_claude-pc_to-codex-pc_REVIEW_PS-GUIDE-MODEL-VARIANTS-001_round1.md:42","observed":"All six rows match the approved variant table and incumbent pins, including reservations 824320, 998400, 8294400 and 9932800 microUSD. Mutation, near-miss names and wrong profile lookups were refused; copying/replacing records leaves the registry unchanged."},
    {"criterion_id":"binding_validation","result":"pass","kind":"automated","candidate_sha":"de574fdea3a436e98a472320ab532b6ec53875ae","source_ref":"X:/PeerSlate/coordination/codex-pc-mvp1-build/Shared/handoffs/2026-10-13_claude-pc_to-codex-pc_REVIEW_PS-GUIDE-MODEL-VARIANTS-001_round1.md:68","observed":"Local tests plus independent adversarial probes refused required-field disagreement, scope/version/deployment/price/envelope changes and equal-valued bool/float substitutions. The helper proves allocation agreement, not funding/cap authorization; consumers must close outer keys and validate endpoints, as recorded in the nonblocking review."},
    {"criterion_id":"incumbent_byte_identity","result":"pass","kind":"automated","candidate_sha":"de574fdea3a436e98a472320ab532b6ec53875ae","source_ref":"X:/PeerSlate/coordination/codex-pc-mvp1-build/Shared/handoffs/2026-10-13_claude-pc_to-codex-pc_REVIEW_PS-GUIDE-MODEL-VARIANTS-001_round1.md:93","observed":"Independent base/candidate comparison preserved StructuredRequest field order/defaults/repr flags and complete wire hashes for six incumbent requests. Candidate golden/refusal tests also passed against the base, while intended new behavior failed there. Original callers remain unchanged and no global model selection was added."},
    {"criterion_id":"review_and_delivery","result":"pass","kind":"automated","candidate_sha":"de574fdea3a436e98a472320ab532b6ec53875ae","source_ref":"https://dev.azure.com/peerslate19/portfolio-site/_build/results?buildId=4541","observed":"Claude independently passed the exact pushed candidate (fixed independent receipt; review at coordination e1bba9c). Normal PR1357 current-target CI4541 succeeded at 2026-10-13T05:57:34.58154Z on synthetic merge3279cb030999b89817cf73e69ce0b297c0642b84, source348a79a9b5a6ec06429e408919906d604b631c2c and target5378590f6fd8e33c97fe6fd86973ad80d56be785; all required policies approved. This final evidence-only tail must also pass the ordinary current-head policy before merge; reviewed runtime bytes remain unchanged."}
  ]
}
```

## Current evidence and limits

- Execution resumed on Dot's explicit continuation after its verified allowance-reset condition. Named records, narrow matrix and deterministic binding validators are implemented and locally verified; independent review and implementation merge remain pending. No real provider call or permanent model adoption.
- Original activation CI 4533 rejected `activated_from_main` after main advanced. The same control branch was normally merged with current main and its selected base corrected in `20664f94`; PR 1355 then passed ordinary current-target CI. No new branch/worktree, force push or policy bypass.
- Jev status `bcec5601-e522-4fe7-8dd9-6a8d7f63efcc`: unavailable, `ongoing_paused_transport_failure`. Mandatory regression/matrix checks retained; ordinary source-backed judgment used for record/validation focus without retries or alternate connection.

## Checkpoint results and exact next step

- Negative tests were written and observed failing before changing contracts: four newly approved Sol 6.1 request pairs were refused, and the named-record lookup/validators were absent. Rejected combinations and the three pre-change incumbent wire hashes already passed.
- First implementation verification: 64 tests PASS (the original 57 foundation tests plus seven new variant test methods). A later type-tampering test exposed equal-valued bool/float acceptance inside nested binding dictionaries; recursive exact-type comparison corrected that, and the tampering test now passes.
- At the saved pause, nine focused methods had four subcase errors in `test_four_new_variants_use_the_bound_foundation_provider_with_fake_transport`: the fixture emitted a deployment alias but omitted the real runtime's explicit configured-deployment identity mode. On resumption, source inspection confirmed that cause. The fixture now uses the real mode; new wrong-alias/wrong-version cases prove rejection remains intact. Production provider/identity validation source is unchanged.
- Current verification: `python -B -m unittest discover -s tests/ai_foundation -q` PASS 103 tests (0.374s); `python -B -m unittest tests.test_resume_intake_runtime tests.test_resume_intake_service -q` PASS 110 tests (0.709s), with the existing process-local CI placeholder key. All are fake-provider tests, no paid calls. Complete results and tool provenance are retained in the current session and the review verification receipt.
- Self-review of the complete owned diff found no outstanding finding. Changed runtime path is only `services/ai_foundation/contracts.py`; the added test module and this fixed evidence file are the other candidate paths. Server composition/adapter and local installation consumption remain explicitly assigned to packages 3 and 1. The next step is Claude's exact-SHA independent review, then receipt/acceptance mapping, normal current-target CI and accepted merge.

## Independent review and delivery

Claude PC reviewer `session:9fb18da7-d312-4e90-a956-7f3718e5969f` passed exact candidate `de574fdea3a436e98a472320ab532b6ec53875ae`, with three explicitly nonblocking Minor findings, during 2026-10-13 05:13–05:40 UTC (review time reported at minute precision). Full review is the coordination file referenced above, introduced at coordination `e1bba9c14d39a8a4cf86c2e8275d9822e73933d3`.

The reviewer independently reran 103 foundation tests and 110 intake tests, the exhaustive request acceptance matrix and 70+ adversarial probes. Its whole no-Playwright export comparison found identical pre-existing failure sets at base/candidate (16 errors, 19 failures, 271 skipped; +10 passing new tests). That comparison is regression evidence, **not a claim of a green whole suite or accepted Azure CI**. Normal current-target CI remains required.

The writer accepts the nonblocking disposition without changing reviewed code. Packages 1 and 3 must close outer settings/factory schemas, validate the endpoint, retain exact per-ledger-purpose cap ceilings and distinguish this ongoing 100-call ledger helper from hosted 1–6-call budget guards. Existing consumers already close their settings; this candidate activates no consumer or spending path. The independent probes supplement local coverage; matrix proof is precisely constructor refusal before provider creation. These are retained consumer boundaries, not findings falsely marked fixed in this candidate.

Current delivery state: independent review PASS and all five criteria mapped after normal PR1357 CI4541 succeeded. Only the fixed receipt/evidence tail changed after review; the final evidence-only head still requires the normal current-target policy before accepted merge. No implementation merge, installation, real-model qualification or production release is claimed yet. Jev review-triage skip: first eligible status remains transport-paused in this assignment; no retry or evaluation. The independent PASS, pre-committed scope and required consumer controls determine this disposition.
