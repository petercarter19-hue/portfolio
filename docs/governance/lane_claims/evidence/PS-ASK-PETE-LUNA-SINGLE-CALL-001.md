# Ask Pete Luna single-call implementation evidence

## Pre-implementation baseline and fixed acceptance contract

The accepted planning base is `0fd3c0671a4542b52476bd65d30b52acf86a6e00`. Before changing product code, the assigned writer ran the focused existing Foundry route suite from the clean durable worktree with Python 3.13.3. It passed 31 tests under the current two-call design. This establishes a reproducible source baseline, not live Luna reliability. The current one-use diagnostic separately recorded two HTTP 200 calls and a rejected summary support verdict; it did not reveal the checker's reason. Production, enablement and paid sampling remain separate.

## Reviewed candidate and candidate-bound checks

The exact implementation candidate is `2740c920b7582ccbd2abafcf0e896141fb71277d`. The writer ran the complete Ask Pete suite (152 tests), complete shared AI Foundation suite (64 tests), and focused fact-selection/Foundry-route suite (37 tests); all passed with fake transport and no paid model call. `git diff --check` and clean claimed-surface write preflight passed. Actual route fixtures demonstrate one strict stateless low-reasoning selection call for each of four purposes, including a two-paragraph 100–140-word recruiter brief with three distinct cited role passages. All 15 approved records are present exactly once as ordered source lines; generated text supplies only fact IDs, and server code renders factual excerpts and exact citation spans. This preserves provenance, not proof that Luna chooses the most relevant facts.

The first exact-candidate independent review found a malformed-mode HTTP 500 defect and failed. The corrected candidate's independent review by `session:01a0f06e-59f1-7411-a6dc-1946b89fa031` passed with that finding resolved and no open findings. The external review report and receipt are retained at `X:/PeerSlate/evidence/PS-ASK-PETE-LUNA-SINGLE-CALL-001/independent-review-2740c920/`. No production deployment, live Luna answer, target-deployment schema acceptance, latency, or cost improvement is established by these local tests or the one-call count.

```package-acceptance-json
{
  "schema_version": 1,
  "package": "PS-ASK-PETE-LUNA-SINGLE-CALL-001",
  "plan_sha": "ac8f5c2e4494f4709ae102567a2b75d9f043c6ce",
  "baseline": [
    {
      "command": "python -B -m unittest tests.ask_pete.test_live_foundry",
      "exit_code": 0,
      "observation": "Pre-change Foundry route baseline: Ran 31 tests in 0.832s, OK; the suite exercises the existing two-call generation/support path with fake transport and no paid Luna call."
    }
  ],
  "criteria": [
    {
      "id": "one-call-bound",
      "expected": "Each public Foundry attempt makes at most one strict stateless low-reasoning Luna call, with no support call, retry or resample, inside the existing 20-second whole-request deadline and one-call spend cap.",
      "verification": "Exercise actual /api/chat with fake transport, inspect request body, credential count, terminal metrics, deadline, incomplete-response and capacity cases."
    },
    {
      "id": "approved-fact-containment",
      "expected": "All 15 current full manifest-approved public records remain available; each has a selectable complete atom. Every visitor-facing factual passage and citation comes from an authorized current source's exact version/span, with no Luna-authored factual prose released.",
      "verification": "Load the real catalog, assert full input reconstruction and per-record atom coverage, then test foreign, duplicate, malformed, stale, cross-subject and wrong-purpose selections plus exact response-to-source spans."
    },
    {
      "id": "purpose-and-envelope",
      "expected": "All four public purposes produce useful positive response.v1 answers. The recruiter brief is a coherent two-paragraph 100-140-word answer with at least three distinct cited facts, a meaningful bounded gap, exactly two neutral interview questions and a private non-executing handoff.",
      "verification": "Drive real-catalog positive fake Luna selections through /api/chat for public answer, recruiter brief, evidence finder and interview preparation; assert content, word counts, purpose quality and source relationships, then exercise unknown/ambiguous states separately."
    },
    {
      "id": "trust-and-degradation",
      "expected": "Private, secret and instruction-override requests refuse; scoring/ranking is never emitted; unsupported or malformed selection and provider, deadline or source-currentness failures release no factual claims and retain useful unavailable behavior without a second call.",
      "verification": "Run focused negative route and atom tests for privacy/refusal precedence, ranking redirection, malicious source/question text, invalid output, changed sources, timeout and late events."
    },
    {
      "id": "provider-isolation",
      "expected": "The Haiku path, shared Foundry provider and intake callers retain their existing prompt, schema and behavior; no public visual or production setting changes occur.",
      "verification": "Run focused existing Haiku/provider tests and inspect the exact candidate changed-path diff and call sites."
    }
  ],
  "candidate_sha": "2740c920b7582ccbd2abafcf0e896141fb71277d",
  "checks": [
    {
      "criterion_id": "one-call-bound",
      "result": "pass",
      "kind": "automated",
      "candidate_sha": "2740c920b7582ccbd2abafcf0e896141fb71277d",
      "source_ref": "tests/ask_pete/test_live_foundry.py:test_one_stateless_call_and_full_catalog;test_generation_timeout_cannot_retry;test_incomplete_response_is_rejected",
      "observed": "The actual route made one strict, stateless, low-reasoning Luna request and one credential call; incomplete, timeout and capacity paths made no retry or support call within the whole-request deadline."
    },
    {
      "criterion_id": "approved-fact-containment",
      "result": "pass",
      "kind": "automated",
      "candidate_sha": "2740c920b7582ccbd2abafcf0e896141fb71277d",
      "source_ref": "tests/ask_pete/test_fact_selection.py:test_complete_fifteen_record_catalog_is_transmitted_once_with_usable_atoms;test_subject_and_purpose_authorization_still_bind_exact_citations;test_invalid_and_extra_model_fields_cannot_release_a_fact",
      "observed": "All 15 full approved records reconstruct exactly from one content-lines representation, each supplies a selectable atom, every fact citation names its exact source span, and forged, cross-subject or wrong-purpose selections fail authorization or the selection contract."
    },
    {
      "criterion_id": "purpose-and-envelope",
      "result": "pass",
      "kind": "automated",
      "candidate_sha": "2740c920b7582ccbd2abafcf0e896141fb71277d",
      "source_ref": "tests/ask_pete/test_live_foundry.py:test_all_four_public_purposes_have_positive_route_answers;tests/ask_pete/test_fact_selection.py:test_longer_ranked_shortlist_still_fits_a_complete_brief",
      "observed": "Fake Luna selections produced successful response.v1 answers for all four purposes; the recruiter route gave two paragraphs, 100-140 words, three different role-source citations, a bounded evidence gap, two neutral questions and a private nonexecuting handoff."
    },
    {
      "criterion_id": "trust-and-degradation",
      "result": "pass",
      "kind": "automated",
      "candidate_sha": "2740c920b7582ccbd2abafcf0e896141fb71277d",
      "source_ref": "tests/ask_pete/test_live_foundry.py:test_nontext_mode_returns_useful_unavailable_after_one_call;test_private_override_refuses_without_paid_call;test_source_change_during_generation_or_serialization_cannot_escape;X:/PeerSlate/evidence/PS-ASK-PETE-LUNA-SINGLE-CALL-001/independent-review-2740c920/FINAL_REVIEW_RECEIPT.json",
      "observed": "Malformed array, object, Boolean and integer modes return HTTP 200 unavailable with no facts after one call; private and override requests refuse before the token call, ranking is redirected, and changed sources withhold the answer. Independent review resolved the prior HTTP 500 finding."
    },
    {
      "criterion_id": "provider-isolation",
      "result": "pass",
      "kind": "automated",
      "candidate_sha": "2740c920b7582ccbd2abafcf0e896141fb71277d",
      "source_ref": "python -B -m unittest discover -s tests/ask_pete -p test_*.py;python -B -m unittest discover -s tests/ai_foundation -p test_*.py;services/ask_pete/runtime.py",
      "observed": "The complete Ask Pete suite passed 152 tests and AI Foundation passed 64; the diff changes only the Foundry-only prompt path, leaving Haiku prompt and shared provider/intake source bytes unchanged."
    }
  ]
}
```
