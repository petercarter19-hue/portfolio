# Ask Pete Luna support deadline repair

## Observed baseline and bounded change

The root-operated, one-use flag-off canary on deployed source `2b577cf4f45028d415b52259f6c2a4f41ab6ba31` returned unavailable. Luna generation completed HTTP 200 in 8.156 seconds and local grounding quality passed in 1 ms. A second whole-answer support call started after a successful credential step, but no response was observed before the 20.001-second whole-request deadline. Two calls started, one finished; second-call usage is unknown. This proves the new support-path deadline failure, not the cause of the earlier public-page failure. Evidence: `X:/PeerSlate/evidence/PS-ASK-PETE-LIVE-TELEMETRY-001/luna-release-20260928/root-canary-result.json` and `root-canary-fixture.json` in the same directory.

Candidate `d49e416f1412d6c314c46e0c101f85cbdbae327a` changes only the support verdict to Luna reasoning effort `none`; generation remains `low`. The full approved source records and proposed answer still go to the separate strict support call. The 20-second deadline, two-call limit, no retries, exact citation/product checks, refusal rules and unavailable fallback remain in place. Microsoft's current [Foundry model matrix](https://learn.microsoft.com/en-us/azure/foundry/openai/how-to/reasoning) lists `gpt-6-luna` with both Responses API structured outputs and reasoning effort `none`. That documents API support; it does not establish live speed or semantic quality.

## Candidate checks and independent review

The writer ran the focused real-route and shared-provider fake-transport suites on the candidate: 59 tests and 39 subtests passed in 3.98 seconds, zero paid calls. The tests cover per-phase request options, independent support rejection, refusal, deadline/capacity, currentness, and privacy behavior. `git diff --check` was clean; the pushed branch contains only the three claimed source/test paths. Independent exact-candidate review passed with no findings: `X:/PeerSlate/evidence/PS-ASK-PETE-LIVE-SUPPORT-001/independent-review-d49e416f/FINAL_REVIEW_RECEIPT.json`, SHA-256 `4A8FB1F89FCD60A8C45EFB85E2B585EB02F8D5EC1ECD512AFD2CB39392CFC90F`.

Live quality, factual support judgment, and click-to-visible speed are unverified. The earlier canary is consumed. The root manager alone owns a fresh exact-source release, one-use model operation and public-page acceptance.

## Acceptance-plan timing exception

The writer committed candidate `d49e416f` at 2026-09-28 23:43:20 UTC before committing the fixed acceptance plan required by `START_HERE.md` section 7. No pre-implementation test baseline command was captured. A later retrospective attempt to run the same tests in the sparse control checkout failed during collection because `app` and `services` were absent there; it does not measure product behavior. The live canary above is the actual pre-change behavioral baseline. The plan and criteria below were recorded after implementation and are labeled retrospective. `plan_sha` remains null; it is not a claim of compliance with the normal timing rule.

Pete directly gave the root manager full authority for future exceptions. The root manager recorded a one-time exception **only to plan timing** for this exact package and candidate in `X:/PeerSlate/evidence/PS-ASK-PETE-LIVE-SUPPORT-001/ROOT_PLAN_TIMING_EXCEPTION.json` (`root-luna-support-plan-timing-20260928-v1`). The exception keeps source bytes, independent review, normal CI/server policies, delivery preflight, and production/live gates intact. It does not alter the global rule or validator. The agent-executed `package_acceptance.py` result remains incomplete and is reported below after the evidence commit; no PASS is asserted.

Actual post-evidence command: `python -B scripts/package_acceptance.py check --package PS-ASK-PETE-LIVE-SUPPORT-001 --candidate d49e416f1412d6c314c46e0c101f85cbdbae327a`. Exit code 1; raw result: `{"result": "incomplete", "reason": "exact pre-implementation plan SHA is missing"}`. This is the expected unresolved timing gate under the one-time manager exception, not an automated acceptance PASS.

```package-acceptance-json
{
  "schema_version": 1,
  "package": "PS-ASK-PETE-LIVE-SUPPORT-001",
  "plan_sha": null,
  "baseline": [
    {
      "command": "Read root-canary-result.json for the one-use Build 3738 flag-off diagnostic",
      "exit_code": 0,
      "observation": "Retrospectively read the pre-change live result: generation HTTP 200 in 8.156 seconds, then support transport unfinished at the 20.001-second whole-request deadline; the canary outcome was unavailable."
    }
  ],
  "criteria": [
    {
      "id": "phase-specific-effort",
      "expected": "Generation remains Luna low; only the separate full-evidence strict support verdict uses Luna none.",
      "verification": "Inspect both request bodies through the existing real /api/chat fake-transport test."
    },
    {
      "id": "fail-closed-grounding",
      "expected": "Unsupported or malformed support verdicts, invalid evidence, refusal contract violations and timeout still withhold a public answer, with no extra provider call.",
      "verification": "Run focused Ask Pete real-route negative and deadline tests and inspect the scope diff."
    },
    {
      "id": "shared-provider-isolation",
      "expected": "The shared Foundry answer constructor permits the explicit none option with strict schema while other default and structured-intake paths retain their contracts.",
      "verification": "Run the shared provider suite and inspect call sites and the separate structured-intake method."
    }
  ],
  "candidate_sha": "d49e416f1412d6c314c46e0c101f85cbdbae327a",
  "checks": [
    {
      "criterion_id": "phase-specific-effort",
      "result": "pass",
      "kind": "automated",
      "candidate_sha": "d49e416f1412d6c314c46e0c101f85cbdbae327a",
      "source_ref": "tests/ask_pete/test_live_foundry.py:test_real_route_has_two_low_strict_stateless_calls_and_safe_metrics",
      "observed": "The real route's two outgoing request bodies use reasoning low then none, with strict schema and no tools."
    },
    {
      "criterion_id": "fail-closed-grounding",
      "result": "pass",
      "kind": "automated",
      "candidate_sha": "d49e416f1412d6c314c46e0c101f85cbdbae327a",
      "source_ref": "tests/ask_pete/test_live_foundry.py;writer focused pytest output in session:01a0ea20-0c57-7521-90a2-ab3e1af19322",
      "observed": "Focused suite passed 59 tests and 39 subtests; unchanged negative, refusal, privacy and deadline cases run through the changed provider path."
    },
    {
      "criterion_id": "shared-provider-isolation",
      "result": "pass",
      "kind": "automated",
      "candidate_sha": "d49e416f1412d6c314c46e0c101f85cbdbae327a",
      "source_ref": "services/ai_foundation/azure_foundry.py;tests/ai_foundation/test_azure_foundry_provider.py;independent-review-d49e416f/FINAL_REVIEW_RECEIPT.json",
      "observed": "The existing answer option now permits none only when paired with a strict schema; default answer calls and the separate xhigh structured-intake path are unchanged."
    }
  ]
}
```
