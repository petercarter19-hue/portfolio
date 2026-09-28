# Ask Pete failure telemetry acceptance

The earlier deployed live request returned unavailable without usable phase evidence. A subsequent one-use actual-adapter diagnostic succeeded, which proves capability once but does not explain the failed request. This package corrects diagnosability only. Root remains sole production executor; no paid calls or production changes occur in this repository assignment.

Seven implementation/test surfaces are admitted. Existing prompt, model, identity, 20-second request deadline, two-provider-call maximum, no-retry rule, citations and whole-answer support contract remain controlling. Independent reviewer: session:01a0c0a4-9342-7163-9052-f16ea0eee843. Owner/root direction and selected outcome are bound in the claim.

The following plan is committed alone before implementation. Its SHA is filled into the candidate before review; exact candidate proofs are recorded only after actual verification.

```package-acceptance-json
{
  "schema_version": 1,
  "package": "PS-ASK-PETE-LIVE-TELEMETRY-001",
  "baseline": [
    {
      "command": "python -B -m unittest discover -s tests/ask_pete -p test_live_foundry.py -q",
      "exit_code": 0,
      "observation": "Existing 20 actual-route, semantic enforcement, deadline and capacity cases pass with stub providers and process-local Werkzeug3.1.9; no network inference. Baseline is rerun in the admitted worktree before committing this plan."
    }
  ],
  "criteria": [
    {
      "id": "visible-safe-sink",
      "expected": "Dedicated INFO sink emits bounded structured records under debugfalse/rootWARNING without enabling general Flask/SDK logging, propagation or duplicate handlers. A payload-free readiness marker can be retrieved after deployment before a paid check.",
      "verification": "Actual sink output with rootWARNING and repeated configuration; fixed readiness marker; no provider calls."
    },
    {
      "id": "failure-stage",
      "expected": "Credential, transport/non2xx, response validation, grounding contract, support rejection, source/currentness, serialization, capacity and deadline failures have fixed stage/reason evidence.",
      "verification": "Inject deterministic failures through real route/runtime/provider seams and inspect captured safe records alongside unchanged public results and provider call counts."
    },
    {
      "id": "privacy",
      "expected": "Only allowlisted keys and strict bounded scalar values enter logs; no user question, source, answer, citation, header, token, exception text or traceback. Request correlation is server-generated and bounded.",
      "verification": "Unknown/nested/wrong-type/nonfinite/oversized values and secret sentinels across failure inputs never occur in real sink output."
    },
    {
      "id": "answer-invariants",
      "expected": "Existing grounded acceptance/refusal behavior, prompts/model/identity, maximum two calls and no retries remain unchanged. Sink failure never changes answer acceptance.",
      "verification": "Existing route/grounding suites plus sink-failure injection and scope diff; all inference uses deterministic stubs."
    },
    {
      "id": "deadline-and-usage",
      "expected": "Capacity/deadline reasons preserve20second bounded work semantics, abandoned work retains its slot, late events cannot overwrite terminal outcome, and known paid usage remains visible while unavailable usage remains unknown.",
      "verification": "Existing bounded-thread tests plus forced timeout/late worker and paid-response validation failure; no new live calls."
    }
  ],
  "plan_sha": "e67145852c19761c20fa7da357dcddc4b8428b4e",
  "candidate_sha": "8c6b39d740267ed63ac696909393717dbc7e4157",
  "checks": [
    {
      "criterion_id": "visible-safe-sink",
      "result": "pass",
      "candidate_sha": "8c6b39d740267ed63ac696909393717dbc7e4157",
      "kind": "automated",
      "source_ref": "tests/ask_pete/test_live_foundry.py:431;tests/ask_pete/test_live_foundry.py:449;services/ask_pete/diagnostics.py:63",
      "observed": "With root WARNING and Flask debug false, the dedicated INFO sink emitted correlated route and request records. Repeated setup produced one handler and one payload-free sink_ready marker."
    },
    {
      "criterion_id": "failure-stage",
      "result": "pass",
      "candidate_sha": "8c6b39d740267ed63ac696909393717dbc7e4157",
      "kind": "automated",
      "source_ref": "tests/ask_pete/test_live_foundry.py:468;tests/ask_pete/test_live_foundry.py:492;tests/ask_pete/test_live_foundry.py:511;tests/ask_pete/test_live_foundry.py:528",
      "observed": "Credential, transport, HTTP, response validation, answer contract, support rejection, source, currentness, serialization and capacity injections produced fixed distinct reasons with the original unavailable result and bounded provider counts."
    },
    {
      "criterion_id": "privacy",
      "result": "pass",
      "candidate_sha": "8c6b39d740267ed63ac696909393717dbc7e4157",
      "kind": "automated",
      "source_ref": "tests/ask_pete/test_live_foundry.py:458;tests/ask_pete/test_live_foundry.py:431;services/ask_pete/diagnostics.py:38",
      "observed": "Nested, unknown, wrong-type, oversized and nonfinite fields were omitted; secret sentinel, question and answer text were absent from captured real sink output."
    },
    {
      "criterion_id": "answer-invariants",
      "result": "pass",
      "candidate_sha": "8c6b39d740267ed63ac696909393717dbc7e4157",
      "kind": "automated",
      "source_ref": "tests/ask_pete/test_live_foundry.py:630;tests/ask_pete/test_live_foundry.py:115;services/ask_pete/foundry_provider.py:182",
      "observed": "A failing telemetry sink did not change a supported answer or two-call count. The full 146-case Ask Pete suite passed with stubbed provider replies and unchanged grounding/refusal enforcement."
    },
    {
      "criterion_id": "deadline-and-usage",
      "result": "pass",
      "candidate_sha": "8c6b39d740267ed63ac696909393717dbc7e4157",
      "kind": "automated",
      "source_ref": "tests/ask_pete/test_live_foundry.py:542;tests/ask_pete/test_live_foundry.py:569;tests/ask_pete/test_live_foundry.py:599;tests/ask_pete/test_live_foundry.py:492;tests/ask_pete/test_live_foundry.py:653",
      "observed": "A request timeout stayed terminal; deterministic stalled-sink and real-logger interleaves marked delayed worker events late, with no late transport call. Paid-response validation failures kept available usage, and abandoned work retained its capacity slot."
    }
  ]
}
```

## Limits and release handoff

Passing offline tests establishes telemetry behavior, not live reliability or historical cause. Required independent review and normal CI precede merge. A separate root-owned exact-source deployment must verify the readiness marker is retrievable before any newly bounded live acceptance operation; successful diagnostic evidence alone never grants re-enable authority.

Jev checkpoint: root explicitly selected the previously investigated minimum telemetry correction and its failure/privacy checks. These baseline/criteria checks directly verify that contract; no unsettled prioritization or meaningful alternative warrants another advisory call. Prior trace-priority result28856885-cb3d-4304-ac11-6f7ec9a32d6c remains recorded in parent evidence.

## Review and candidate-bound verification

Independent Protected review: FINAL_REVIEW_RECEIPT.json, exact candidate `8c6b39d740267ed63ac696909393717dbc7e4157`. Full Ask Pete unittest suite: 146 passed, zero paid calls; output retained in `X:/PeerSlate/evidence/PS-ASK-PETE-LIVE-TELEMETRY-001/ask-pete-tests-final-candidate.txt`. The review does not prove live reliability or explain the prior unavailable response.
