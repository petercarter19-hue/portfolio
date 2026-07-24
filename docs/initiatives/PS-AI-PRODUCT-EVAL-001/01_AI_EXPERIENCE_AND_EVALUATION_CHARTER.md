# AI experience and evaluation charter

## 1. Inventory: purpose before model

| Experience | Member / visitor purpose | Allowed grounding | Output boundary | Current status |
| --- | --- | --- | --- | --- |
| Ask Pete / Ask [Name] | Ask a public-facing person/site question | Approved public sources only | Public answer with source support and uncertainty; no private retrieval | Public typed Ask Pete exists; expansion is not authorized here |
| Ask Slate | Receive private, contextual member help | Only server-authorized member sources and member-provided context | Reviewable private proposal; no write or publication | Planned |
| Interview coaching | Practice a response and understand a useful next revision | Member-provided answer, selected question, explicitly authorized evidence | Feedback and optional draft; member keeps/changes/rejects | Current Studio behavior is separately governed; advanced contract planned |
| Workshop / Build assistance | Shape private work or a possible future | Authorized selected material only | Contextual proposal, never a hidden second truth store | Planned |
| Résumé-page / Story / Project help | Make a purpose-specific proposal | Exact selected source set and destination contract | Draft/proposal with clear destination; never automatic update | Planned / separately governed |
| Return-value intelligence | Notice a source-linked pattern or possibility | Authorized source-linked history | Private, correctable, dismissible interpretation | Planned |

No product page gains a generic AI box merely because a model is available. The
page-purpose and non-redundancy gate decides whether the proposed help has a
member purpose distinct from direct typing, Voice, evidence, and an existing
workflow action.

## 2. Ask Pete and Ask Slate are different trust products

| Boundary | Ask Pete / Ask [Name] | Ask Slate |
| --- | --- | --- |
| Audience | Public visitor | Signed-in member |
| Sources | Approved public source set | Server-authorized private sources plus selected member input |
| Identity | No private member identity premise | Server-derived member identity before retrieval |
| Output | Helpful public answer with citations/limits | Source-aware private proposal with review and correction |
| Forbidden behavior | Private retrieval, pretending to know a visitor, private write | Cross-owner retrieval, hidden source expansion, silent action |

Neither surface may be treated as a persona with authority over the member. The
name is a product/workflow label, not permission to hallucinate a personal
relationship or make consequential decisions.

## 3. Prompt and programming architecture

The application should construct each request as a bounded, inspectable
workflow rather than send a large all-purpose prompt:

1. Deterministically identify the requested workflow and server-derived actor.
2. Enforce authorization before source retrieval; create the minimal permitted
   evidence packet and record its source versions.
3. Apply a versioned task instruction, voice policy, rubric, and output schema.
4. Call the selected model/provider through a provider adapter with the minimum
   necessary context and explicit time/cost limits.
5. Validate schema, citations/source references, prohibited claims, and
   confidence/no-evidence behavior deterministically.
6. Show a member-visible proposal with sources, uncertainty, and accept/change/
   reject controls.
7. Record privacy-safe evaluation signals, corrections, failures, latency, and
   cost without retaining more private content than the applicable lifecycle
   policy permits.

Models do not authorize, retrieve, choose an audience, persist canonical facts,
or perform writes. An AI proposal and an accepted member edit remain distinct
data classes with provenance.

## 4. Evaluation evidence and safety suite

Every candidate workflow needs a versioned human-reviewed golden case set. It
must include strong, weak-but-truthful, vague, unsupported, no-result,
off-topic, sensitive, contradictory, sparse, long, and non-native/ordinary
voice inputs. Add workflow-specific cases before selection rather than trying to
repair quality after release.

The suite also contains adversarial and privacy cases: prompt injection in
member-provided material; instructions that request secret sources; cross-owner
source identifiers; malicious files/links where relevant; capability-unavailable
states; provider timeouts; malformed structured output; unsupported metrics;
and requests for automatic publishing, sharing, or rewriting.

Human review is the primary adjudication for truthfulness, helpfulness, voice,
and appropriateness. Model-as-judge may prioritize or summarize candidate
differences, but is secondary: it cannot be the only acceptance evidence, label
itself independent, or define the product's desired coaching tone.

## 5. Versioning, measurement, and launch threshold

Record the model/provider, resolved version/alias, task instruction version,
rubric version, retrieval/source policy version, output schema version, and
evaluation-set version for each evaluation and release candidate. Record
privacy-safe latency, cost, response validity, grounding/support rate, human
usefulness, correction/override rate, refusal/no-evidence appropriateness,
failure recovery, and safety exceptions.

No universal numeric threshold is invented here. Pete approves the measurable
threshold for each workflow after reviewing representative outputs. At minimum,
launch evidence must show that the candidate:

- follows source, privacy, and no-write boundaries with no unresolved critical
  failure;
- handles no-evidence and unavailable conditions honestly;
- is materially more useful than the non-AI baseline for the chosen task;
- preserves natural voice and does not introduce unsupported claims;
- fits an explicit latency and cost envelope; and
- has member correction/rejection, monitoring, and a safe stop/rollback path.
