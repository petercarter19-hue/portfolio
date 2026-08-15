# AI surface sequence

**Recorded:** 2026-08-14
**Purpose:** prevent a cross-site AI review from becoming one broad,
unreviewable prompt exercise.
**Runtime effect:** none.

## One-surface-at-a-time rule

The inventory answers only two platform-level questions: what provider-backed
AI surfaces exist, and what order should they be reviewed in. Detailed prompt,
knowledge, retrieval, guardrail, evaluation, and model work is limited to the
active surface. A later surface cannot borrow an unaccepted decision from the
active one merely because both currently call the same provider.

| Order | Surface | Current provider-backed jobs | Deep-review state |
| --- | --- | --- | --- |
| 1 | Interview Studio | answer review, answer improvement, nudge, grounded/generic model answer | Owner-review direction complete through Shared Constitution section 9 and specialists 1-5B; runtime architecture/implementation separately gated |
| 2 | Opportunity Slate | extraction concerns, statement interpretation, alignment analysis | Queued immediately after Interview acceptance; owner reports the 2026-08-14 imported-source journey as substantially broken |
| 3 | Ask Pete | grounded public-profile answer generation | Queued; owner reports iPad failure or severe latency requiring real-device measurement |
| 4 | Workshop | review and proposal assistance behind Workshop contracts | Queued |
| 5 | Additional surfaces | any provider call found after this map was recorded | Inventory-only until explicitly ordered |

Ask Pete Direct is not included as an AI surface. It is a private unanswered-
question inbox, not a model-generated answering system.

## Current provider map

The 2026-08-14 repository baseline uses Anthropic-compatible Messages calls.
This document does not select Anthropic, Azure OpenAI, or any other provider for
future releases.

- Interview Studio calls `claude-haiku-4-5-20251001` directly from `app.py`.
- Ask Pete uses the same Haiku model through
  `services/ask_pete/provider.py` and `services/ask_pete/runtime.py`.
- Opportunity Slate declares a mix of Haiku and Sonnet models in
  `services/opportunity_analysis_service.py`.
- Workshop declares Haiku in `services/workshop_review_service.py`.

Provider/model evaluation is deferred until a surface has an accepted job,
knowledge contract, golden set, scorecard, and owner threshold. A brand or one
good demonstration is not a selection method.

## Required dossier for every surface

Each surface must eventually have its own accepted record of:

1. user job and specialist identity;
2. system instruction and prompt version;
3. allowed knowledge, tools, and authorization-before-retrieval rule;
4. prohibited knowledge and actions;
5. input and output contracts;
6. privacy, safety, injection, and unsupported-claim guardrails;
7. length, voice, uncertainty, and refusal policy;
8. provider/model, timeout, latency, usage, and cost observations;
9. useful unavailable and malformed-output behavior;
10. synthetic golden cases and human-reviewed scores;
11. owner decisions and unresolved tradeoffs;
12. a separately authorized implementation package for accepted runtime work.

## Stop condition

Interview remains the only deep-review surface until Pete accepts its intended
specialists and boundaries. This package may identify defects and propose
requirements, but it cannot alter a production prompt, provider, model,
retrieval rule, endpoint, UI, or release setting.
