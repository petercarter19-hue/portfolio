# Required-check repair and CI parity

Owner-selected scope: session01a11384-f656-73b3-b57a-ad2952f1ffad, event evt-b086cad6-30e9-494e-9e98-d022ee6094bc. Base42a811990f251d1dfbb10d82c4d46ed1216b8258. Protected independent review; repository through merge, production withheld.

Ordinary activation PR1310 passed Azure4366 and merged before implementation. Deliver this implementation separately with the accepted claim unchanged. Future structurally valid mixed repair activations must run full CI using accepted target boundaries. Local hash-bound owner and independent review admission stays required. This does not authenticate external attestations or grant authority.

```package-acceptance-json
{
  "schema_version": 1,
  "package": "PS-DELIVERY-REPAIR-CI-PARITY-001",
  "plan_sha": "be8ffa1e442e5d22d1f29b74b7c25534868cd8f0",
  "baseline": [
    {
      "command": "python -B -m unittest tests.test_delivery_change_classification tests.test_delivery_preflight.RepairAdmissionTests",
      "exit_code": 0,
      "observation": "40 tests passed in 37.721 seconds before implementation at42a81199; full output in external repair-parity-baseline.txt."
    }
  ],
  "criteria": [
    {
      "id": "repair_full_ci",
      "expected": "Fresh exact Protected scanner, classifier and test-only repair activations use full CI, equally for supported caller references, and never the control-only shortcut.",
      "verification": "Real temporary Git target/source/merge fixtures in tests.test_delivery_change_classification."
    },
    {
      "id": "target_boundary",
      "expected": "Accepted target authority rejects malformed, colliding, overbroad, noncanonical, modified existing, multiple, product, pipeline, extra-tail, deleted, renamed and nonordinary-mode repair deltas; candidate validator code cannot expand or execute its own admission.",
      "verification": "Adversarial temporary Git fixtures exercising classify against accepted target validators."
    },
    {
      "id": "existing_guards",
      "expected": "Ordinary activation shortcut, guard-only full route, unknown provenance fallback, final-job coherence and external owner/hash/independent review requirements remain effective; classifier repair surfaces are supported without unrelated expansion.",
      "verification": "Existing classification tests and RepairAdmissionTests including new classifier-file admission and stale-review denial."
    }
  ],
  "candidate_sha": "3e3bfc709d89460361fa52835a3d090df72ce793",
  "checks": [
    {
      "criterion_id": "repair_full_ci",
      "result": "pass",
      "kind": "automated",
      "candidate_sha": "3e3bfc709d89460361fa52835a3d090df72ce793",
      "source_ref": "X:/PeerSlate/ChatGPT/evidence/Azure-capacity-audit-2026-10-09/repair-parity-focused-2.txt",
      "observed": "Corrected focused suite: 51 tests passed in 109.620s. Real Git fixtures verify scanner, classifier and test-only Protected repair activations route to full CI for supported caller references, never the control-only shortcut."
    },
    {
      "criterion_id": "target_boundary",
      "result": "pass",
      "kind": "automated",
      "candidate_sha": "3e3bfc709d89460361fa52835a3d090df72ce793",
      "source_ref": "X:/PeerSlate/ChatGPT/evidence/Azure-capacity-audit-2026-10-09/INDEPENDENT_REPAIR_PARITY_3e3bfc70.md",
      "observed": "Writer's corrected 51-test suite covers adversarial target-boundary cases. Independent delta review passed a fresh forced-core.filemode=true probe of all five mode/deletion/rename subcases in 16.854s, including real committed before/after modes. Accepted target-only classifier and claim blobs are unchanged from the prior independently tested candidate; that earlier complete review is reused, not claimed as rerun."
    },
    {
      "criterion_id": "existing_guards",
      "result": "pass",
      "kind": "automated",
      "candidate_sha": "3e3bfc709d89460361fa52835a3d090df72ce793",
      "source_ref": "X:/PeerSlate/ChatGPT/evidence/Azure-capacity-audit-2026-10-09/repair-parity-focused-2.txt",
      "observed": "The corrected 51-test command retains ordinary activation, guard-only full routing, unknown-provenance fallback, final-job coherence and local owner/hash/review coverage, including classifier-file admission and stale-review rejection. Independent delta review confirmed unchanged preflight, classifier, START_HERE and admission-test blobs."
    }
  ]
}
```

Pre-implementation design PASS is retained externally in INDEPENDENT_REPAIR_CLASSIFIER_DESIGN.md. Jev unavailable with ongoing_paused_transport_failure (status4c10358a-ee8e-4d2d-8e81-095680d96abd); direct accepted-source analysis and independent review used, no retry or paid request.

External evidence root: X:\PeerSlate\ChatGPT\evidence\Azure-capacity-audit-2026-10-09. No product, pipeline, cloud, schema or production change belongs to this package.

Writer verification: first watched the scanner/classifier/test-only regressions fail against unchanged classifier rejections, plus classifier-file local admission fail at the unsupported boundary (repair-parity-red.txt and repair-parity-admission-red.txt). After implementation, the exact baseline command passed51 tests in109.986s (repair-parity-focused-1.txt). Real Git cases cover target authority, full routing/coherence, supported caller parity, fresh exact claims, both claim sets/collisions, nonordinary modes, deletions/renames and unrelated-file refusal. Existing local owner/hash/review checks remain, including stale-review rejection for the newly supported classifier files.

Writer self-review: bounded64-line classifier addition uses only accepted target validator/lifecycle modules, validates the whole target/candidate claim sets, and returns full only; no control-only or unknown-provenance behavior is weakened. Preflight change adds exactly the classifier and its tests to the existing repair boundary. Documentation preserves external owner/review/custody obligations. git diff --check passed. Independent exact-candidate review and Azure CI remain pending at candidate freeze.

Independent acceptance: agent:/root/azure_reliability_review passed exact candidate8864c3f982beeb145df1f38dbc39a0aee2a9104f at2026-10-09T14:24:13Z with no actionable findings,51 fresh tests in110.927s and two supplemental Git boundary probes. Report and receipt preserved. The post-review tail changes only this evidence file and the fixed receipt. Azure CI remains a separate required server proof; no cloud or production release is claimed.


CI correction: Azure4371 secret scan passed, but application CI exposed a test-fixture platform difference. With core.filemode=true, git add -A restored working-file modes over index-only chmod fixtures, and an index/working-tree mismatch prevented checkout in the prior-executable case. The same2failures/1error were reproduced locally with that setting (repair-filemode-reproduction.txt). The bounded correction sets core.filemode=false only in the mode-fixture test and asserts actual committed before/after modes. The forced-setting reproduction then passed (repair-filemode-corrected.txt). Classifier and admission runtime bytes are unchanged. A new exact candidate and independent delta review are required; the prior candidate acceptance above is historical, not current merge permission.

Separate Claude-owned failure in the same run: one of143 integrated browser journeys timed out opening #resume-intake[open] at test_resume_intake_browser.py:263, called by test_missing_composer_explicit_recreate_preserves_monotonic_fence. Root cause remains unproven; exact log37 retained and Claude handoff updated. No onboarding source change, waiver or blind retry. Jev remains paused; direct failure reproduction supplies the bounded debugging fallback.

Corrected focused suite: the original combined command passed51 tests in109.620s (repair-parity-focused-2.txt). Writer delta self-review confirms only the temporary mode-fixture setup and real tree-mode assertions changed; all classifier/preflight/documentation runtime blobs match the first reviewed candidate. git diff --check passed. The failure evidence and prior candidate/receipt remain preserved in Git and the external audit folder.

Current independent acceptance: agent:/root/azure_reliability_review passed exact candidate3e3bfc709d89460361fa52835a3d090df72ce793 at2026-10-09T14:53:24Z without actionable findings. The fresh independent probe forced core.filemode=true at initialization and passed all five mode-method subcases in16.854s. It verified unchanged runtime blobs and inspected the writer's corrected51-test result; the earlier independent51-test runtime review is reused, not represented as rerun on this correction. Report: INDEPENDENT_REPAIR_PARITY_3e3bfc70.md. This tail changes only the fixed receipt and evidence. Normal Azure CI on the final source remains required; no browser failure disposition or production release is asserted here.
