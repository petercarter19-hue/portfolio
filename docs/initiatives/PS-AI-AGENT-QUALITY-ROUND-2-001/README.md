# PS-AI-AGENT-QUALITY-ROUND-2-001 - Specialist AI quality execution round

**Status:** Planned - not active; owner marked this work urgent.
**Authority placement:** Execution round/addendum under
`PS-AI-PRODUCT-EVAL-001`, not a competing AI constitution.
**Risk path:** Protected for any prompt, provider, model, retrieval, or release
change.
**Runtime status:** This charter changes no prompt, model, provider, tool,
endpoint, evaluation gate, or live behavior.

## Outcome

Verify that every AI entry point uses the right specialist in the right place,
with expert instructions, bounded sources/tools, explicit guardrails, useful
failure behavior, and human-reviewed evaluation. Interview support must become
an exceptional interview expert, not a generic text generator.

## Required inventory

For every AI surface, record:

- user job and the specialist responsible;
- allowed sources, tools, and retrieval authorization;
- prompt/instruction version and output schema;
- guardrails, privacy boundary, length policy, and fallback;
- model/provider configuration, context size, latency, cost, and owner;
- golden cases, graders, human reviewers, launch threshold, and current release
  truth.

The review must decide whether Interview is best served by one routed
specialist or separate coaching, model-answer, and nudge specialists. That
choice is evidence-driven, not predetermined by this charter.

## Interview expert contract

The Interview specialist must:

- classify the question before answering or coaching;
- judge directness, ownership, evidence, clarity, relevance, and result;
- use STAR when it helps, without forcing every answer into a formula;
- distinguish strong, promising-but-incomplete, weak, off-topic, contradictory,
  confidential, and genuinely insufficient evidence;
- explain what is good and what is not with specific, proportionate feedback;
- never invent metrics, responsibilities, experiences, or certainty;
- preserve the member's natural voice rather than manufacturing corporate copy;
- calibrate answer length to the question. A quick factual question deserves a
  concise answer; a substantial behavioral or scenario question may justify a
  fuller answer. It must never default automatically to a three-minute speech.

## Evaluation set

Include short/direct, behavioral, conflict, failure, leadership,
technical/case, ambiguous, custom, weak/vague, off-topic, no-result,
contradictory, confidential, prompt-injection, insufficient-source, and provider
failure cases. Human review must score grounding, length fit, useful
specificity, unsupported claims, tone/voice, schema adherence, safety, latency,
cost, and unavailable behavior.

## Site Audit owner checkpoint

Before selecting runtime changes, walk Pete through the AI surface map in plain
language: which specialist handles each job, what it can see, what it cannot do,
the guardrails, sample good/bad results, evaluation evidence, and remaining
tradeoffs. Runtime corrections must be split into bounded implementation
packages with their own acceptance and release proof.

This checkpoint is about product AI quality. It is not the banked code/Azure
learning walkthrough.
