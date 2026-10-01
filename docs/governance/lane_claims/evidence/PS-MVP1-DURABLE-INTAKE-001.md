# MVP1 durable intake prerequisite

Protected source package. Owner authority: session:01a0f424-566c-70c2-bf77-55043f130ff5/owner-selection:2026-09-30/remaining-mvp1-durable-intake. Actual writer: session:01a0f435-a3f3-7772-b22b-49050330b295; configured and native turn-context verified gpt-6.1-sol/high. Accepted activation and source baseline: f91ed278e7e43299850069aea0aecc759fdbd0a3. Write preflight passed with exact native identity before this plan.

The initial pytest launch could not collect tests because that runner was unavailable; after three consistent availability refusals the approach stopped. The supported existing unittest runner then executed the same focused test modules successfully. This is a pre-change source baseline, not SQL engine proof. Full launcher observations remain in package-local external evidence.

Scope preserves accepted MVP1 engine/persona/progress results. Parent owns concrete isolated-engine admission/execution and assigns the independent reviewer. No schema application, deployment, enablement, original-bytes retention implementation, provider/factory wiring or production mutation occurs in this source package. New migration files use SQL FIles/Migrations/ directly; legacy proposed migration bytes remain unchanged.

```package-acceptance-json
{
  "schema_version": 1,
  "package": "PS-MVP1-DURABLE-INTAKE-001",
  "plan_sha": "653e3586d5a1a19cda6055693fc0fddcb4f56850",
  "baseline": [
    {
      "command": "X:/PeerSlate/runtimes/development/Scripts/python.exe -B -m unittest tests.test_resume_intake_sql tests.test_my_data_drafts tests.test_resume_intake_service tests.test_my_data_intake_sources",
      "exit_code": 0,
      "observation": "Actual pre-change source f91ed278e7e43299850069aea0aecc759fdbd0a3: 142 tests ran in 0.496 seconds; OK. Unittest used the existing X:/PeerSlate/runtimes/development runtime."
    }
  ],
  "criteria": [
    {
      "id": "draft_cas",
      "expected": "Owner-scoped composer drafts survive independent repository reloads; optimistic saves retain losing input, same-request retries replay, discard/expiry preserve revision tombstones, and old client versions cannot overwrite a recreated draft.",
      "verification": "Focused durable SQL adapter/service contract tests and separately admitted real SQL two-connection CAS/reload/replay/ABA oracles."
    },
    {
      "id": "draft_isolation",
      "expected": "Draft commands change only the authenticated owner draft map, preserve canonical/source/receipt state, resolve attachment availability after purge on reload, and retain policy-selected inactivity expiry without adopting upload/voice ceilings.",
      "verification": "Focused owner isolation, expiry, snapshot-preservation and purge-versus-draft-save tests; admitted SQL oracle."
    },
    {
      "id": "source_atomicity",
      "expected": "A keep-separate action binds to one active owner-qualified source version and server-held normalized candidate; canonical/source/candidate/receipt writes commit or roll back together with no silent canonical write.",
      "verification": "Closed command-contract tests, forged/stale/foreign candidate negative tests, admitted SQL canonical rollback and two-connection source-consumption oracles."
    },
    {
      "id": "source_replay_purge",
      "expected": "One extracted candidate can be consumed at most once across workers; same-key/lost-response and new-key winner replay recover the owner receipt; purge removes member wording and cannot resurrect a candidate.",
      "verification": "Focused source replay/redaction tests and admitted two-connection keep-versus-keep and purge-versus-keep SQL oracles."
    },
    {
      "id": "schema_gate",
      "expected": "Only one additive Intake002 migration/rollback/verifier and registry entry are introduced; prerequisite source bytes remain unchanged; genuine generic migration gates prove Intake002 plus each currently ungated prerequisite, with guarded rollback and private structural evidence.",
      "verification": "Registry check, structural/runner tests and separately admitted actual generic govern_sql_migrations emitted proofs with exact executable/rollback/verifier manifest hashes."
    },
    {
      "id": "proof_boundary",
      "expected": "The new proof driver reuses pinned SQL/client images and the accepted 18-wheel runtime, requires exact source and one-invocation authority, rejects production/client DSNs and unsafe topology, and verifies identity-bound cleanup.",
      "verification": "Proof-runner admission/manifest/cleanup tests and actual parent-operated isolated proof evidence."
    },
    {
      "id": "compatibility_review",
      "expected": "Accepted intake, draft and source behavior passes focused regressions; the full claimed diff is self-reviewed and an independent Protected review approves the exact frozen source candidate.",
      "verification": "Focused unittest suite, writer self-review evidence and parent-assigned independent exact-SHA receipt. Required current-target CI and accepted merge/close remain separately recorded lifecycle gates."
    }
  ],
  "candidate_sha": "ccbfa4689b9e6313fc41b47be1154a8096650111",
  "checks": [
    {
      "criterion_id": "draft_cas",
      "result": "pass",
      "kind": "automated",
      "candidate_sha": "ccbfa4689b9e6313fc41b47be1154a8096650111",
      "source_ref": "X:/PeerSlate/evidence/PS-MVP1-DURABLE-INTAKE-001/actual-engine-3866/resume-intake-sql-proof/evidence.json; sha256:c1dc1c93c2d268b3fd8ad6d02c5e698203268457879061ca56ac2a07c8331d20",
      "observed": "Actual3866 durable reload, two-connection CAS, lost reply replay, discard/expiry/recreate fences pass. Exact executable/service bytes preserved at final candidate."
    },
    {
      "criterion_id": "draft_isolation",
      "result": "pass",
      "kind": "automated",
      "candidate_sha": "ccbfa4689b9e6313fc41b47be1154a8096650111",
      "source_ref": "X:/PeerSlate/evidence/PS-MVP1-DURABLE-INTAKE-001/actual-engine-3866/resume-intake-sql-proof/evidence.json; sha256:c1dc1c93c2d268b3fd8ad6d02c5e698203268457879061ca56ac2a07c8331d20",
      "observed": "Actual3866 owner isolation and purge-versus-save two-connection scenarios pass; source tests verify attachment refresh without inactivity renewal. Exact final source unchanged from engine."
    },
    {
      "criterion_id": "source_atomicity",
      "result": "pass",
      "kind": "automated",
      "candidate_sha": "ccbfa4689b9e6313fc41b47be1154a8096650111",
      "source_ref": "X:/PeerSlate/evidence/PS-MVP1-DURABLE-INTAKE-001/actual-engine-3866/resume-intake-sql-proof/evidence.json; sha256:c1dc1c93c2d268b3fd8ad6d02c5e698203268457879061ca56ac2a07c8331d20",
      "observed": "Actual3866 normalized candidate binding, stale/foreign/forged/inactive owner refusal, atomic canonical/source/receipt consumption and injected rollback pass; unparented Impact remains proposal. Exact final executable/source bytes match engine."
    },
    {
      "criterion_id": "source_replay_purge",
      "result": "pass",
      "kind": "automated",
      "candidate_sha": "ccbfa4689b9e6313fc41b47be1154a8096650111",
      "source_ref": "X:/PeerSlate/evidence/PS-MVP1-DURABLE-INTAKE-001/actual-engine-3866/resume-intake-sql-proof/evidence.json; sha256:c1dc1c93c2d268b3fd8ad6d02c5e698203268457879061ca56ac2a07c8331d20",
      "observed": "Actual3866 same/new-key replay, two-worker keep and purge-versus-keep pass; same-key replay after purge does not resurrect wording/history or duplicate canonical facts."
    },
    {
      "criterion_id": "schema_gate",
      "result": "pass",
      "kind": "automated",
      "candidate_sha": "ccbfa4689b9e6313fc41b47be1154a8096650111",
      "source_ref": "X:/PeerSlate/evidence/PS-MVP1-DURABLE-INTAKE-001/actual-engine-3866/resume-intake-sql-proof/evidence.json; sha256:c1dc1c93c2d268b3fd8ad6d02c5e698203268457879061ca56ac2a07c8331d20",
      "observed": "All6 actual generic gates pass forward/reapply/verifier/rollback/reapply; exact emitted proof objects imported. All14 closure forward/rollback/verifier digests match accepted engine plan; guarded history rollback pass."
    },
    {
      "criterion_id": "proof_boundary",
      "result": "pass",
      "kind": "automated",
      "candidate_sha": "ccbfa4689b9e6313fc41b47be1154a8096650111",
      "source_ref": "X:/PeerSlate/evidence/PS-MVP1-DURABLE-INTAKE-001/actual-engine-3866/resume-intake-sql-proof/evidence.json; sha256:c1dc1c93c2d268b3fd8ad6d02c5e698203268457879061ca56ac2a07c8331d20",
      "observed": "Actual3866 pinned SQL2022/client18-wheel acquisition, fixed invocation-owned databases/internal no-port topology and all4 identity/absence cleanup checks pass. Driver/runtime unchanged at final candidate."
    },
    {
      "criterion_id": "compatibility_review",
      "result": "pass",
      "kind": "automated",
      "candidate_sha": "ccbfa4689b9e6313fc41b47be1154a8096650111",
      "source_ref": "X:/PeerSlate/evidence/PS-MVP1-DURABLE-INTAKE-001/SOURCE_FINAL_INDEPENDENT_REVIEW_ccbfa468.json; sha256:4204551f2e08fa807222a50f11ea387f4d4c33d15c56e3dd22d8c7a1a971ee2e",
      "observed": "379 prior focused writer checks,47 current affected checks and19 independent database checks pass; exactccbfa468 Protected review PASS. Named CI3867 closed allowlist failure corrected by adding only three accepted Intake002 names/count177to180; all exact union/disjointness and existing guards retained. No runtime/SQL/driver/registry changes."
    }
  ]
}
```

Jev checkpoints: investigation and evidence prioritization were settled by the assigned exact repository contracts; regression and writer review selection consist of the mandatory criteria above, so those four checkpoints have specific non-eligibility records. The eligible server-held-value binding choice followed Jev attempt c63b5983-b7f8-40c8-a37e-9f7034872126 (server_normalized_candidate probability0.98/confidence0.97); outcome remains pending, with raw result/annotation and required central report retained outside the repository.

Implemented source: owner durable composer reload and CAS, retained revision tombstones, lifecycle fences and attachment refresh without inactivity renewal; atomic source-bound keep-separate command with complete typed normalized value binding, owner/version fences, idempotent structural history and actionable parent-required Impact proposals. Accepted extraction/provider source remains unchanged. No factory wiring or product enablement occurs here.

Actual isolated engine acceptance: parent-operated Azure DevOps build3866 at source a3553171f02816fefe36df180d1f764aecd55d3b, plan57e622742cf86ba5f5547fc811bc4279cf4dc307132906dc04fdc387d5310c9f and manifest08490dfca006e17f6f65b7b7e7f0968a6013b3486d25871ebabfd9634a65d659 passed all14 cases, all6 actual generic migration gates and all4 identity/absence cleanup checks. Exact raw evidence X:/PeerSlate/evidence/PS-MVP1-DURABLE-INTAKE-001/actual-engine-3866/resume-intake-sql-proof/evidence.json SHA256 c1dc1c93c2d268b3fd8ad6d02c5e698203268457879061ca56ac2a07c8331d20; acceptance ROOT_ENGINE_ACCEPTANCE_3866.json in the same package evidence root. Previous3857/3861/3865 attempts remain failed evidence with verified cleanup, never reused admissions.

Only the six exact emitted generic gate objects were imported into registry.json. All14 migration forward/rollback/verifier executable digests match the accepted3866 plan; existing source SQL bytes remain unchanged. The four admitted compatibility tests now accept honest null before proof or require a structurally valid registry proof whose digest matches executable SQL. Focused final source/SQL/proof/extraction/provider/compatibility regressions:379 tests pass in2.584seconds. ScriptDom previously parsed the final forward including three dynamic procedure bodies with zero syntax errors; static checks are not engine evidence. Final exact-SHA independent review, current-target CI, accepted merge and normal claim close remain required. No production schema application or deployment has occurred.

Final independent Protected review: PASS exact 7ebf5b0e7e7d683cceaafa92f19c1fa00e106f77; X:/PeerSlate/evidence/PS-MVP1-DURABLE-INTAKE-001/SOURCE_FINAL_INDEPENDENT_REVIEW_7ebf5b0e.json; sha256:a047652284a242c560a1a08954f38f6cdf58448fcb20df48844921ca8912b50d. Candidate-bound criterion checks above preserve the immutable plan and baseline. Current-target CI, merge and normal close follow separately.

Required CI3867 identified the closed database allowlist fixture missing exactly the three reviewed Intake002 procedures (7069 tests, one failure). Accepted one-file claim extension PR1202/maina020bb2a/CI3868 allowed tests/test_database_service.py; its literal expected group and closed count were updated without changing runtime or SQL. Focused affected checks47pass; independent reviewer database checks19pass. Final independent Protected review PASS exact ccbfa4689b9e6313fc41b47be1154a8096650111; X:/PeerSlate/evidence/PS-MVP1-DURABLE-INTAKE-001/SOURCE_FINAL_INDEPENDENT_REVIEW_ccbfa468.json; sha256:4204551f2e08fa807222a50f11ea387f4d4c33d15c56e3dd22d8c7a1a971ee2e. Same runtime PR1201 will receive current-target CI; accepted merge/claim close remain pending.
