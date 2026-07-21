# PeerSlate AI Model and Role Routing

**Operational standard:** July 20, 2026

**Current-model snapshot:** Verify the available model and resolved alias in the
actual product before each major package. Model names, limits, prices, and plan
access can change; the one-manager/one-writer/evidence workflow remains stable.

## The short answer

PeerSlate does not need a chain of agents independently redesigning the same
work. Use:

```text
one designated manager creates and accepts one durable package
        ↓
one sole writer implements, tests, and reviews the complete diff
        ↓
one fresh independent reviewer only when risk/size warrants it
        ↓
the same writer corrects accepted findings
        ↓
Pete/designated manager accepts; writer completes Azure release/closeout
```

Changing brands is not automatically an independent review. A fresh context,
clear review-only scope, exact branch/SHA, and evidence matter more.

## Stable role rules

- Each package names exactly one manager and one active writer. For product
  implementation, the manager ordinarily reviews while the writer writes; they
  may use the same vendor but may not be simultaneous writers on one branch. A
  governance-only package may explicitly assign the manager as its sole writer,
  provided no second writer is active and the package still receives a fresh
  complete-diff review before release.
- The manager owns product decisions, scope, sequencing, shared-governance
  reservations, visual authority, conflict resolution, and final acceptance.
- The writer owns implementation, complete-diff self-review, corrections,
  tests, evidence, PR readiness, and approved release/closeout.
- An independent reviewer challenges the completed diff against the approved
  package. It does not receive an open-ended “redesign this” instruction.
- The original writer fixes accepted review findings; do not hand the branch to
  a fourth session for routine corrections.
- Every handoff uses repository artifacts, branch, exact full SHA, tests,
  screenshots/infrastructure evidence, known gaps, and forbidden scope—not a
  pasted chat transcript.
- Premium models are reserved for decisions or reviews where marginal quality
  changes the outcome. Deterministic tests and smaller models handle inventory,
  extraction, transformation, and log summaries.

## Current Codex/OpenAI routing

Official OpenAI guidance describes GPT-5.6 Sol as the flagship for complex
work, Terra as the everyday workhorse, Luna as the clear/repeatable-work tier,
and Ultra as maximum reasoning with automatic delegation. It also recommends
using the lowest reasoning effort that reliably succeeds.

| Work | Recommended choice | Why |
|---|---|---|
| Foundational product/data/privacy architecture; constitutional documents; complex migration; high-risk cross-domain review | **GPT-5.6 Sol, Extra High or Ultra** | Highest judgment/polish; Ultra only when work splits cleanly into independent evidence lanes |
| Difficult implementation or debugging where ambiguity/risk remains high | **GPT-5.6 Sol, High/Extra High** | Deep reasoning without automatic multi-agent overhead by default |
| Normal implementation, tests, documentation, maintenance, bounded refactors | **GPT-5.6 Terra, Medium/High** | Strong everyday tool use and cost/quality balance |
| File inventory, extraction, classification, formatting, trace matrices, log/test summarization | **GPT-5.6 Luna, Low/Medium** | Clear repeatable outcomes at lower cost |
| Near-instant focused text-only code iteration when available | **Codex Spark** | Preview optimized for small interactive changes; not final architecture or multimodal/visual authority |
| Independent high-risk Codex review | **Fresh GPT-5.6 Sol, High/Extra High** | Review exact diff/SHA against fixed requirements; do not re-author scope |

Use **Ultra** for packages like the present Journal constitutional
reconciliation, broad authorization/privacy architecture, major migrations, or
evidence work with genuinely parallel lanes. Do not use Ultra for a one-file
copy edit, routine test fix, or a second pass over an already approved design.

For current OpenAI model guidance, verify:

- https://learn.chatgpt.com/docs/models
- https://developers.openai.com/api/docs/guides/latest-model

The first source says the default Power setting uses GPT-5.6 Sol at medium,
Sol is for complex open-ended/high-value work, Terra for everyday work, Luna
for clear repeatable work, and Ultra adds automatic subagent delegation.

## Current Claude routing

As of this snapshot, Anthropic officially offers Fable 5 and Sonnet 5, and
Opus 4.8 is its high-judgment Opus release. “Sonic” is not an official model
name; Peter should verify the active picker because the intended name is almost
certainly **Sonnet**. “Claude Table” was likely **Claude Fable**.

| Work | Recommended choice | Why |
|---|---|---|
| Exceptional foundational architecture, long-horizon multi-stage work, major migration | **Claude Fable 5** | Anthropic positions it for its most ambitious, long-running coding and knowledge work; expensive, so use once |
| Default Claude Code implementation, ordinary planning/debugging/refactoring/docs | **Claude Sonnet 5** | Anthropic positions it across the software lifecycle with strong efficiency |
| Fresh independent high-risk requirements/privacy/regression review | **Claude Opus 4.8** | Strong judgment and self-critique; review-only brief avoids duplicate architecture |
| Read-only exploration, inventories, file discovery, mechanical summaries | **Claude Haiku 4.5 / Explore agent** | Fast, lower-cost context reduction |

Official sources:

- https://www.anthropic.com/claude/fable
- https://www.anthropic.com/claude/sonnet
- https://www.anthropic.com/news/claude-opus-4-8
- https://code.claude.com/docs/en/model-config

Fable access and billing vary by plan and changed around July 2026; verify the
actual plan/picker before assuming it is included. In Claude Code, use `/model`
and `/status` to confirm what the session resolved. Model aliases can change.

## Recommended workflows by risk

### Foundational/high-risk product package

Use for Journal architecture, authorization, public projection, messaging,
private AI retrieval, consequential migrations, major route maps, and release
security boundaries.

1. One Sol Ultra **or** Fable manager creates the architecture—never both.
2. Pete/designated manager accepts the durable package/visual authority.
3. Terra/Sol or Sonnet 5 becomes sole implementation writer, based on risk.
4. Writer tests and performs complete-diff self-review.
5. Fresh Opus 4.8 or Sol reviews requirements/privacy/regressions when the risk
   warrants independence.
6. Same writer corrects findings and refreshes evidence.
7. Pete/designated manager accepts; writer completes Azure PR/pipeline/live
   closeout.

When a high-judgment architecture is already accepted and preserved in a
durable package, do not send it to another premium model to “build the
architecture” again. If independence is valuable, give a fresh reviewer the
exact package plus branch/SHA and ask for bounded contradiction, privacy,
security, regression, and evidence findings.

### Ordinary feature package

1. Terra or Sonnet plans within an approved package.
2. The same session implements, tests, and self-reviews.
3. Use a separate reviewer only for material privacy/security/data/visual risk
   or evidence conflict.
4. Manager/Pete accepts.

### Mechanical/governance propagation

1. Luna, Haiku, or Terra performs inventory/formatting/cross-reference work.
2. Deterministic tests and exact diff prove the result.
3. Premium review is unnecessary unless product meaning changed.

### Medium Claude plan/execute shortcut

Claude Code's `opusplan` alias uses Opus in plan mode and Sonnet in execution.
It can replace two sessions for medium work, but inspect `/status` because
aliases and current model availability change. For foundational PeerSlate work,
an approved repository package followed by a fresh writer is clearer.

## Which surface to use

| Surface | Best PeerSlate use |
|---|---|
| ChatGPT Work / Codex desktop manager | Multi-document product architecture, governed files, images, verification, long-running repository coordination |
| Codex CLI/IDE/desktop writer | Repository implementation, tests, Git/Azure evidence, complete-diff review |
| ChatGPT image generation | All requested concept imagery, visual exploration, and image editing; selected output becomes one named visual authority |
| Claude Chat | Focused ideation/critique and short product questions |
| Claude Cowork | Long-running multi-document deliverables when its extra usage is justified |
| Claude Code | Repository implementation, testing, branch evidence, and code review |
| Claude Design | Only when Peter specifically wants an interactive prototype; do not create a competing visual authority beside the selected ChatGPT design |

## Visual workflow

Peter's preferred imaging lane remains ChatGPT/image generation. Use:

```text
ChatGPT creates/refines concepts
→ Pete selects one exact production-intent authority
→ manager writes the interaction/truth/accessibility contract
→ one Codex or Claude Code writer implements
→ writer compares desktop/mobile/failure states to the authority
→ optional fresh reviewer challenges the diff
→ Pete/manager gives visual-product acceptance
```

Do not ask both ChatGPT and Claude Design to independently define the same
screen unless the task is explicitly a comparison study. Store the selected
asset and its truth boundary in the initiative package.

## Token and session economy

- Put stable product rules in Bible/Roadmap/governance; repo workflow in
  `AGENTS.md`/`CLAUDE.md`; package scope in the initiative; reusable procedures
  in skills. Do not paste all four into each prompt.
- Start a fresh session for a different package. Compact only while continuing
  the same objective.
- Use exact file paths and SHA instead of replaying discussions.
- Delegate verbose searches, inventories, and test-log reduction to smaller
  subagents; keep final judgment with the manager/writer.
- Keep agent teams small and give each a bounded independent question.
- Ask the reviewer for ranked findings with requirement/file evidence, not a
  rewrite.
- Do not run two premium architecture passes “for confidence.” Cross-vendor
  review is valuable only when it is independent and question-driven.

## Required handoff block

Every substantial handoff contains:

1. package, status, owner decision, designated manager, and sole writer;
2. authoritative base, branch, exact full SHA, and whether writer ownership is
   retained or relinquished;
3. governing requirements, visual authority, truth boundary, and explicit
   exclusions/deferred items;
4. complete changed-file list and migration/infrastructure impact;
5. focused/full/accessibility/responsive/security tests and exact results;
6. screenshots or infrastructure evidence and every accepted deviation;
7. open findings, risks, conflicts, and required next reviewer/action;
8. PR/pipeline/live state stated separately; and
9. clear stop conditions.

The receiving agent reads the package and complete diff. It does not rebuild
the requirements from chat.

## PS-AI-OPS requirements

- **PS-AI-OPS-001:** One package shall have exactly one designated manager and
  one active branch writer.
- **PS-AI-OPS-002:** Architecture shall be authored once and stored durably.
- **PS-AI-OPS-003:** The writer shall self-review the complete diff before
  handoff.
- **PS-AI-OPS-004:** Independent review shall be risk-based and review-only.
- **PS-AI-OPS-005:** The same writer shall fix accepted review findings.
- **PS-AI-OPS-006:** A model switch shall not be treated as evidence of
  independence when the same context or unbounded task is reused.
- **PS-AI-OPS-007:** Foundational work uses Sol Ultra/Extra High or Fable once,
  not both by default.
- **PS-AI-OPS-008:** Normal implementation defaults to Terra or Sonnet.
- **PS-AI-OPS-009:** Mechanical work defaults to Luna, Haiku, or deterministic
  scripts/tests.
- **PS-AI-OPS-010:** Premium reviewers are reserved for material risk.
- **PS-AI-OPS-011:** Imaging uses one selected ChatGPT authority unless Peter
  explicitly requests a comparison.
- **PS-AI-OPS-012:** Chat transcripts are not the source of truth.
- **PS-AI-OPS-013:** Handoffs require exact branch/SHA/evidence and ownership
  status.
- **PS-AI-OPS-014:** Implementation, self-review, acceptance, merge,
  deployment, and live verification shall be reported separately.
- **PS-AI-OPS-015:** Current model/alias availability shall be verified in the
  actual surface before a major run.
- **PS-AI-OPS-016:** Model cost/limit pressure may change model choice but shall
  not remove required evidence or authority controls.
- **PS-AI-OPS-017:** Cross-vendor review shall target a defined risk question,
  not repeat the complete workflow.
- **PS-AI-OPS-018:** A package may use multi-agent work only when lanes are
  independent, bounded, and synthesizable by the active manager/writer.
