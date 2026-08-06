# Slice 1 contract — grounded answer boundary

## Outcome

This non-production slice establishes a reusable, provider-neutral boundary
for PeerSlate AI products. Ask Pete's recruiter brief is the reference case;
the contracts contain no Pete-specific product logic and can support other
products through distinct adapters, purposes, and authorized sources.

## Execution order

1. A product adapter creates a request with a subject, audience, purpose, and
   optional page context.
2. The caller supplies immutable source versions already retrieved from the
   authoritative domain under its own authorization rules.
3. The gateway rechecks source subject, audience, purpose, uniqueness, and
   content digest before the provider receives any source text.
4. The provider returns a typed answer or JSON-like mapping.
5. The strict decoder rejects unknown fields, invalid enum values, wrong
   primitive types, excessive lengths, and non-private handoffs.
6. The grounding validator verifies every citation against an exact character
   span in an authorized source version and enforces answer-state consistency.
   This proves linkage, not semantic entailment.
7. A product-level evaluator can test whether the validated answer also meets
   interaction criteria such as brief length, evidence count, boundaries,
   follow-ups, and handoff behavior.
8. The caller may render the validated result. Nothing in this slice saves,
   publishes, sends, deletes, or changes canonical truth.

## Trust contract

- `supported` claims require inspectable exact-span citations.
- `partially_supported` claims require evidence and a visible limitation.
- `not_established` is an honest knowledge boundary, not a negative fact.
- `interpretation` is distinct from source evidence and names its limitation.
- public requests cannot use sources approved only for an owner or another
  subject or purpose.
- provider failure yields a useful unavailable state without factual claims.
- a human handoff is a private proposal and is independent from later
  knowledge-review or publication decisions.
- operational traces contain counts, timing, state, and error category only;
  they exclude prompts, questions, source text, excerpts, answers, and contact
  information.
- configurable character and source-count budgets fail before a provider call.
- a trace sink may receive payload-free success, degraded, and failure records;
  a sink failure never changes the product result or masks the original error.

## Evaluation boundary

Deterministic evaluation in this slice measures contract-level properties. It
does not claim semantic correctness, conduct model grading, choose a provider,
or authorize production use. Later model/provider work must add curated cases,
adversarial tests, quality thresholds, and release evidence without weakening
these deterministic checks.

## Explicit exclusions

No route, UI, database or SQL, Workshop or Opportunity behavior, provider
configuration, secret, pipeline, deployment, or production action is included.
