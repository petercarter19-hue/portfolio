# Private persistent test installation

Owner outcome: one private test site on X, real Azure AI in every supported
Resume/Profile workflow, persistent work-history uploads, and Mac/iPad browser
access through Tailscale. A private local owner can have a dummy display name;
uploaded real documents retain their sensitivity. No review ZIP is required
in Pete's ordinary workflow.

This record first fixes repository/controller acceptance criteria. Installation,
real-provider acceptance, and physical Mac/iPad access are separate outcomes;
repository acceptance alone does not establish them. Production authority is
withheld. Existing preview ports and the Coding Dashboard mapping are preserved.

Baseline was observed before any implementation writes in this durable worktree.
External preparation is retained at
`X:\PeerSlate\evidence\PS-LOCAL-REVIEWER-INSTALLATION-001\preparation-live-ai`;
its source-level independent review cleared all findings after 40 offline tests.
That preparation review does not substitute for the final pushed-SHA review.

```package-acceptance-json
{
  "schema_version": 1,
  "package": "PS-LOCAL-REVIEWER-INSTALLATION-001",
  "baseline": [
    {
      "command": "python -B scripts/delivery_preflight.py --package PS-LOCAL-REVIEWER-INSTALLATION-001 --intent write --task-ref session:01a0f3c7-c019-7500-b0e9-18e7c84f93fc --fetch --require-clean",
      "exit_code": 0,
      "observation": "Registered durable worktree is clean at accepted activation main213b15fdabba5036d077a1bc4523f7cfc1eafa76; exact writer, branch and Protected through-merge claim pass. Unrelated worktree observations grant no authority and do not block this claim."
    },
    {
      "command": "Python read-only installation.json, private configuration and provider ledger existence, and state.json size inspection at X:/PeerSlate/local-reviewer",
      "exit_code": 0,
      "observation": "Installed source aef7f5a546d818f71089e4dff370d6a8e2faa415 remains offline, private_profile false, no private-access.json or provider budget ledger, saved state15968bytes."
    }
  ],
  "criteria": [
    {
      "id": "private-owner",
      "expected": "Private mode derives one persistent owner from the exact trusted Tailscale identity and origin, rejects wrong identity/origin and fixture switching, and isolates durable uploads by owner.",
      "verification": "Candidate-bound local_reviewer identity and upload/reload isolation tests plus independent source review."
    },
    {
      "id": "live-provider-composition",
      "expected": "All five supported AI paths use real application provider factories with separate durable reservation scopes, deferred credentials, immutable accepted source/factory bindings, and content-free diagnostics; denied or uncertain calls never replay or reset accounting.",
      "verification": "Candidate-bound provider tests using fake transports through real factories, exact supplied source/interface/allocation checks, and independent source review. Live paid responses remain installation acceptance."
    },
    {
      "id": "durability-and-recovery",
      "expected": "Saved content survives reload; corrupt snapshots, untrusted artifacts and modified controllers fail closed; shutdown drains admitted work and fences queued/new work; update and rollback wait for child lifetime completion before state or manifest changes.",
      "verification": "Candidate-bound persistence, artifact-integrity and shutdown lifetime regression tests plus independent source review."
    },
    {
      "id": "private-setup-and-operation",
      "expected": "One-time private setup protects local files, refuses partial setup and downgrade, preserves the existing installation on preparation failure, and documents Start/Stop and one private bookmark without a review-ZIP workflow.",
      "verification": "Candidate-bound setup/manager tests, Windows ACL verification in isolated disposable storage, and independent source/document review. Live installation and physical-device proof remain explicitly pending."
    }
  ],
  "plan_sha": "bf95bd54bd8b14da9d3b6c070b295b05e91406a6",
  "checks": [
    {
      "criterion_id": "private-owner",
      "candidate_sha": "4577824a8715b00d1b1b3aeab3f66b015cb36bf5",
      "kind": "automated",
      "result": "pass",
      "source_ref": "X:\\PeerSlate\\evidence\\PS-LOCAL-REVIEWER-INSTALLATION-001\\SUCCESSOR_PAIR_FINAL_TEST_BINDING.json",
      "observed": "92 controller checks pass, zero skips: persistent server-derived private owner, trusted identity/origin, foreign original/citation and fixture-switch refusals remain intact. Independent exact candidate review PASS."
    },
    {
      "criterion_id": "live-provider-composition",
      "candidate_sha": "4577824a8715b00d1b1b3aeab3f66b015cb36bf5",
      "kind": "automated",
      "result": "pass",
      "source_ref": "X:\\PeerSlate\\evidence\\PS-LOCAL-REVIEWER-INSTALLATION-001\\SUCCESSOR_PAIR_FINAL_TEST_BINDING.json",
      "observed": "92 checks pass: all five actual factories retain distinct immutable ledger scopes and uncertain-call fences. Fixed V11/V12 hash and source checks admit only reviewed bytes; pair promotion preserves owner, signing key, allocation, profiles, models, rates and caps, defers credentials and dispatches no provider. Same-app refresh with original active request preserves the exact recovery digest and ledger; app-binding changes refuse. Earlier independent real fixed-interface admission/tampering probes remain accepted. Native acceptance is pending."
    },
    {
      "criterion_id": "durability-and-recovery",
      "candidate_sha": "4577824a8715b00d1b1b3aeab3f66b015cb36bf5",
      "kind": "automated",
      "result": "pass",
      "source_ref": "X:\\PeerSlate\\evidence\\PS-LOCAL-REVIEWER-INSTALLATION-001\\SUCCESSOR_PAIR_FINAL_TEST_BINDING.json",
      "observed": "92 checks pass: existing saved content, originals and accounting survive. Private app and factory snapshot select through one atomic manifest; malformed/missing/modified pairs refuse without fallback. Failed preparation and interrupted writes leave original pointer/data/ledger intact; rollback selects the prior pair. Running/undrained workers and active requests refuse binding-changing promotion/rollback under the lifetime lock before content/receipt/manifest changes. Both independently found P2 traps corrected and re-reviewed PASS."
    },
    {
      "criterion_id": "private-setup-and-operation",
      "candidate_sha": "4577824a8715b00d1b1b3aeab3f66b015cb36bf5",
      "kind": "automated",
      "result": "pass",
      "source_ref": "X:\\PeerSlate\\evidence\\PS-LOCAL-REVIEWER-INSTALLATION-001\\SUCCESSOR_PAIR_FINAL_TEST_BINDING.json",
      "observed": "92 checks pass: one-time setup and no reinitialization/downgrade remain intact. Snapshot files are protected within data and hash-pinned; actual Windows nested snapshot ACL apply/verification PASS at03fbc266, and the unchanged ACL function carries forward under final independent review. Maintainer docs describe original lineage versus active pair, Start/Stop/bookmark, and original-binding failure recovery. Physical-device and paid installation acceptance remain separate."
    }
  ],
  "candidate_sha": "4577824a8715b00d1b1b3aeab3f66b015cb36bf5"
}
```


The current independently reviewed source candidate is `4577824a8715b00d1b1b3aeab3f66b015cb36bf5`.
The original preimplementation plan `bf95bd54bd8b14da9d3b6c070b295b05e91406a6`
and its four fixed criteria are preserved. The later installed failures and
bounded recovery direction are recorded contemporaneously in
`OPERATOR_RECOVERY_PLAN.json`; they do not rewrite earlier chronology.

Accepted application source is `3fa759ce997574f60cfb6ad7414b8e850dffab4a`,
verified against runtime merge `1dfcd61d5f9afee21f57af2e1e161085c4199c4e`
and current main `309aad202b59ecb9c863222f0ee002055fedb2f2`.
The fixed V11 and V2 bindings remain unchanged. Supplier runtime/CI/merge proof
is verified; its original acceptance-helper plan deficiency remains an explicitly
Conditional supplier closeout, not a fabricated helper PASS.

The private installation and Tailscale8443 were established with private ACLs;
existing Dashboard443 and other previews were preserved. Actual Windows HTTPS,
owner/origin refusal and a fully styled browser view were verified. Four real
fictional workflows passed: extraction, interview, synthesis and Speech. The
first visitor request returned503 after one nativeHTTP200; native body/status/
model/ID were not retained. Its full329728 reservation and consumed count remain
preserved. No inference of a valid answer or actual-cost settlement is made.

Installed browser acceptance found concurrent static assets could receive503;
cf41 fixed the admission path and passed independent review plus actual browser
verification. Superseded CI3940 failed11 logging assertions because fixture
teardown left global logging disabled; b81 corrected restoration and109 targeted
checks passed. Current combined regression passes285 checks. Exact-source review
of95e8 has no blocking findings, accepts the specific original synchronous-
transport and server-lifetime-lock quiescence proof, and binds the explicit local
operator full-charge recovery. The recovery is separate from validated successful
settlement. One new fictional visitor qualification is bounded and diagnostic;
the original is never replayed. Its final installed result is recorded separately.

PR1212 remains subject to normal required CI and accepted merge. Source acceptance
is not a production deployment or physical-device claim. Physical Mac/iPad browser
and microphone proof requires those devices; the Windows private endpoint is
verified. User workflow is Start plus one bookmark, with no review ZIP step.

Evidence: `X:\PeerSlate\evidence\PS-LOCAL-REVIEWER-INSTALLATION-001`, especially
`OPERATOR_RECOVERY_COMBINED.log`, `LOGGING_RESTORATION_REGRESSION_2.log`,
`OPERATOR_RECOVERY_PROOF.json`, `OPERATOR_RECOVERY_REVIEW.json`,
`INDEPENDENT_OPERATOR_RECOVERY_SOURCE_REVIEW_95e8ead8.json` and
`INSTALLED_PRIVATE_ACCEPTANCE.json`. Prior failed logs/reviews remain retained.

Protected repository authority remains through-merge; production is withheld.
Root writer is session01a0f3c7-c019-7500-b0e9-18e7c84f93fc; the same independent
reviewer was configured gpt-6.1-sol/extra high. Actual runtime settings and complete
token/elapsed telemetry are unavailable; no cost/time savings are inferred.


Final installed-path correction: captured fictional native answer/support both
completed, but the extra controller currentness check ran outside Flask request
context and refused the private identity. Candidate03234 preserved that context
without relaxing the check; exact-source independent review passed. Actual private
Boundary/route tests now cover supported answer/citation/settlement, wrong identity,
missing context and stale authority. Earlier static-identity unit tests had missed
this integration defect. Captured-response replay went from503 to200 with zero
provider calls. Finalc382 adds explicit per-operation diagnostic directories so
this one bounded confirmation retains evidence without overwriting earlier
captures. All289 combined checks pass; the same reviewer binds the final delta.

Both failed native requests remain failures. The original ae9b is operator-resolved
at full329728 with count/history preserved. Second ffb has separate reviewed
quiescence evidence and the same full-charge recovery, never a successful/native
settlement. Manager01a0f424-566c-70c2-bf77-55043f130ff5 authorizes at most one fresh
fictional native HTTPS confirmation after reviewed correction/recovery, with one-use
secure diagnostics and no automatic retry. Final installation acceptance, required
CI/merge and cleanup are recorded from actual outcomes, not inferred from tests.

The one authorized corrected native confirmation returned503. Its completed
native answer cited offsets159:203 while the exact authorized excerpt occurs
at160:204. The unchanged grounding validator correctly rejected the mismatch
before a support call. THIRD_PUBLIC_OFFLINE_DIAGNOSIS.json reproduces the exact
GroundingValidationError with no network or live-state writes; correcting only
the span in memory passes that same validator, solely as causal evidence.
Request c638c14a-8560-46df-af33-8af92301cb07 retains its full329728 active fence.
No fourth native probe, third operator recovery, budget reset or source-validator
relaxation is authorized by the bounded confirmation direction. Controller
source acceptance and the four qualified installed AI features remain distinct
from unresolved visitor-answer reliability and overall installation completion.


CI3944 ran7257 application tests and found one concurrent schema-validation race (149 skipped). All previous eleven logging failures were corrected. A legitimate v2-to-v3 commit could occur between separate validation reads. Final candidate80622cfd wraps those checks in one read snapshot, released before the existing caller transaction. The deterministic red test reproduces the exact refusal;9 focused and79 controller checks pass after correction. The same independent reviewer accepted only this delta. Earlier289 combined checks remain historical evidence, not a replacement for required new CI. No live accounting, recovery, provider operation or allocation change accompanied this correction. Installedc382 remains separately identified pending final source release.

CI3946 then passed the complete application suite (7258 tests,149 skipped) and
the required browser job. Its final delivery coherence check correctly failed
after main advanced from309aad202b59ecb9c863222f0ee002055fedb2f2 to
238932841cca122bf6ca6562fb37c69ffef04900 for the shared citation claim activation.
Both retained disposition artifacts match source73ee2b0e, synthetic merge43b4720
and target309aad; this is a target-drift failure, not a code or browser failure.
This evidence-only tail requests a fresh normal PR merge candidate against the
current target. Reviewed80622cfd code and the original four criteria are unchanged;
the old build is not relabeled successful and no policy is bypassed.


## Successor factory compatibility plan before implementation

The receiver owns this package after accepted transfer PR1220 and supported
reconciliation `ec2ecb27c3059126f2d9ddd175b7b6dac7362689`. The clean write
preflight passed against main `2d18bda2ae1eda7ea739bf71682f028ac47deedf`.
The original acceptance JSON baseline and four criteria remain unchanged.

Pre-change command:
`python -B -m unittest tests.test_local_reviewer.SnapshotTests.test_failed_update_preparation_never_publishes_new_manifest tests.test_local_reviewer.SnapshotTests.test_update_waits_for_listener_closed_child_before_checkpoint_and_promotion -v`
passed two tests with zero skips. Inspection confirms that the existing loader
accepts only the V11 factory hash; the supplied V12 cannot yet compose.

The bounded change admits only the fixed V11 and independently reviewed V12
factory hashes. An explicit accepted-app update can prepare an immutable
private configuration snapshot containing the new factory bytes and the
existing settings with only their factory binding replaced. The installation
manifest selects both app release and configuration snapshot in one atomic
write. The original root configuration remains the initial lineage; a selected
snapshot is the authoritative active pair. This avoids a partly promoted app
and configuration after process death, and the existing previous manifest
selects the prior pair on rollback. Private snapshots live beneath protected
`data`, and their complete bytes are pinned by the manifest.

For `live-provider-composition` and `private-setup-and-operation`, verify fixed
V11/V12 admission, arbitrary/tampered factory and snapshot refusal, exact source
pins, accepted-app-only admission, unchanged owner/signing key/allocation/
profiles/contracts/caps, and no credentials or provider calls. For
`durability-and-recovery`, verify running/undrained and active-reservation
refusal, preparation/pointer-write failure preservation, atomic paired
selection and prior-pair rollback; data and ledger bytes must survive. Repeat
the affected controller suite and obtain independent exact-candidate review.

Installation sequencing remains original app `3fa759ce` with V11 when the new
controller is installed. Resolve request `c638c14a-8560-46df-af33-8af92301cb07`
with fresh quiescence proof and required independent attestation under that
original binding before any accepted successor promotion. Runtime CI waits for
central's stable main release. At most one distinct fictional native Visitor
confirmation is allowed after all prerequisites; a failure fences offline
diagnosis, with no paid retry. No personal-content reset or allowance reset.


### Successor pair source acceptance

Final candidate `4577824a8715b00d1b1b3aeab3f66b015cb36bf5` passed required independent review by
`session:01a0fafc-327e-7481-a330-2a29f452b6fc` with actual Sol6.1/xhigh settings verified.
The full affected suite passed92/0skips. Review identified and closed two P2
issues: active successor rollback could strand recovery, and a shadowed input
name could falsely refuse same-app controller refresh. Both original/current
binding directions are now covered. Exact source hashes, logs and findings
are retained in `X:\PeerSlate\evidence\PS-LOCAL-REVIEWER-INSTALLATION-001\INDEPENDENT_SUCCESSOR_PAIR_REVIEW_4577824a.json` and
`X:\PeerSlate\evidence\PS-LOCAL-REVIEWER-INSTALLATION-001\SUCCESSOR_PAIR_FINAL_TEST_BINDING.json`. The added plan is commit
`07d92d3a`; original plan/baseline/criteria remain unchanged.

Read-only qualification `FICTIONAL_SOURCE_ORIGINAL_PREFLIGHT.json` proves the
one existing source is the exact original fictional QA role, source hash
`388ee8f0131c8da90700b0ee6c648605f778a08685d8c5dc70837bd3fa811fdd`,
with saved generation15/state hash unchanged and no provider composition.
Reverify after accepted promotion before the single native confirmation.
Repository acceptance does not establish original c638 recovery, deployment,
new native success or physical-device acceptance.
