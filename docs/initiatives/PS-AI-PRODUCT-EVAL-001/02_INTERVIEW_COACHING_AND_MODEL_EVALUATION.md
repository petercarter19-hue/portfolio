# Interview coaching, improved-answer, and model-evaluation contract

## 1. The coaching job

The product helps a member understand and improve one answer. It does not grade
the member as a person, rank employability, fabricate expertise, or present an
opaque fit score. If a numerical signal is ever proposed, its meaning, evidence,
member display, and correction behavior require a separate owner decision.

The evaluation looks for answer anatomy appropriate to the question and the
member's actual material:

- relevance and directness;
- clear context and personal ownership;
- specific action, judgment, or contribution;
- result, learning, or honest absence of a result;
- evidence/source support where a source set is supplied;
- clarity, structure, and concision; and
- natural voice without inflation or invented metrics.

The system may request a follow-up instead of grading when the question, target
role, audience, answer, or evidence is too ambiguous to give useful feedback.
It must say what is missing. It must not manufacture a result merely to satisfy
a rubric.

## 2. Required output contract

### What Worked Well

This feedback cites the actual helpful part of the member answer in plain
language. It names one to three concrete strengths and why each improves the
answer for the stated question. It must not give generic praise, praise an
unsupported claim, or imply a strong answer when evidence is absent.

### Improve Next Time

This gives the one or two highest-value next improvements, ordered by impact.
Each item identifies the missing/unclear part and suggests an achievable change
without shaming or a punitive score. If a useful answer needs a fact the model
does not have, it asks for that fact instead of telling the member to invent it.

### Improved Draft

An improved draft is an optional proposal, never a replacement for the original.
It must preserve the member's facts, uncertainty, and natural voice; strengthen
structure and clarity; avoid invented dates, metrics, people, or responsibility;
and identify the material changes and why they were proposed. The member can
accept parts, edit, reject, or retry. Acceptance does not publish, update a
résumé-page, alter Story, or become a canonical record without a separate
explicit member action under that destination's contract.

## 3. Evidence, no-evidence, and disagreement behavior

When a selected source set supports a claim, output ties the claim to that
source/version in a member-understandable way. When no source exists, the system
labels the answer as based on the member's supplied text and does not imply
verification. When the evidence conflicts, is stale, revoked, unavailable, or
insufficient, it says so and offers a narrow next action. It never retrieves
additional private material because the model asked for it.

The member may correct the coaching, remove a source from the task, keep the
original answer, or ask for another approach. Correction signals feed the
evaluation program but do not silently retrain or alter the member record.

## 4. Golden cases and provider selection

Create a human-reviewed case library with question, allowed context, expected
boundaries, rubric annotations, and at least one unacceptable-output example.
For interview coaching include: strong answer; truthful weak answer; no
strengths; no result; vague answer; technical answer with poor explanation;
clear answer with weak evidence; confidential material; contradictory evidence;
empty/off-topic answer; misleading prompt injection; and provider/schema
failure.

Compare provider/model candidates on the same held-out cases. Review grounding,
voice preservation, useful specificity, unsupported-claim rate, follow-up
choice, schema validity, failure behavior, latency, cost, context limits, and
accessibility of the resulting member experience. The current delivery-model
routing document may describe who conducts the work; it does not permanently
select a product model. This is task-based provider evaluation, not a permanent
provider preference. A change of model, instruction, source policy, or output
schema receives regression evaluation before it replaces a released candidate.
