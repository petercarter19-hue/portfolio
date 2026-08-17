# PeerSlate Lean Delivery Workflow

_Owner-directed operating model, 2026-07-31. This is the single delivery
workflow. It replaces repeated startup gates, duplicate status records, and
automatic global holds; it does not relax product, security, privacy, data, or
release integrity._

## The default

1. Follow `START_HERE.md`: inspect the checkout, fetch `origin`, preserve other
   work, and read `CURRENT_BASELINE.yaml`.
2. Select one delivery path below.
3. Do the work, run the evidence that fits its risk, self-review the complete
   diff, and create one proportional completion record.
4. Use an Azure DevOps PR for runtime changes. A merge is not a deployment;
   report pipeline and live verification separately when release is in scope.

No task requires an architecture pass, manager handoff, independent reviewer,
Candidate environment, all-specialist-documents reading, or a full-site audit
unless its delivery path or package specifically triggers it.

## Audit package orchestration

Use this loop for a normal audit-derived product or experience package; its
existing repository package remains the durable link across fresh tasks.

```text
ChatGPT Work manages the package
  -> ChatGPT product reasoning and material visuals
  -> Work approves direction and creates the Codex handoff
  -> Codex repository discovery, architecture, and implementation in Cursor
  -> Grok independent first review of the frozen SHA
  -> Codex adjudication, repair, and verification
  -> Work product and visual acceptance
  -> Pete merge and deployment authorization
  -> Azure deployment and Codex production verification
  -> Work final closeout
```

Grok is review-only on the branch/SHA, diff, and evidence.

Reuse package and handoff records. Do not create a brief, status, handoff, or
Markdown file for every phase unless the
package contract requires it. Keep approval, implementation, review, merge,
deployment, live verification, and closeout as separate truthful states.

### Codex bootstrap prompt

```text
Open START_HERE.md and docs/AI_WORKFLOW.md; fetch origin/main; resume the named
package from its existing package/handoff. Before editing, report phase,
decision, branch/base SHA, writable surfaces, exclusions, and next gate. Do not
create workflow or per-phase status files.
```

## Delivery paths

| Path | Typical work | Required control |
|---|---|---|
| **Routine** | Copy, isolated visual bug within locked authority, local refactor, focused test, documentation | One owner/writer, focused validation, complete-diff self-review. |
| **Bounded** | Approved route or feature within an established package/architecture | Package brief, focused contract tests, ordinary PR/pipeline/live smoke when released. |
| **Protected** | Identity, authorization, privacy, canonical truth, migration, deletion/publication, consequential AI, shared infrastructure/configuration, or materially revised visual direction | Named risk contract, applicable negative/rollback evidence, and independent review when the package requires it. |

When uncertain, begin with Bounded. Escalate to Protected only when a listed
trust boundary is actually touched; state the reason in the completion record.

## Non-negotiable integrity rules

- Treat Azure DevOps `origin/main` as authoritative where reachable; never push
  directly to `main`. Preserve unrelated work and secrets.
- One writer owns a mutable file or surface at a time. A manager is required
  only to resolve a real cross-lane or owner decision, not to repeat a writer's
  review.
- Private is the default. Derive identity server-side and authorize before
  returning or changing protected data.
- Keep canonical truth, source evidence, AI proposals, and derived projections
  distinct. AI proposes; people decide. AI never silently saves, publishes,
  sends, deletes, or changes canonical truth.
- Preserve responsive, accessible, truthful behavior. A demo/fixture/flagged
  capability must be labelled as such.

## Triggered specialist work

Read the following only when relevant:

| Trigger | Authority/evidence |
|---|---|
| Material visual direction or locked-design change | `OWNER_VISUAL_INTEGRITY_STANDARD.md`; ChatGPT creates revised authority and the owner accepts it. |
| Story composition | `OWNER_STORY_COMPOSITION_STANDARD.md`. |
| Capture, Moment, Journal, audience, or projection truth | `PS-JOURNAL-001` and its linked contract. |
| Projects | `PS-PROJECTS-001`. |
| Protected release, migration, identity/security, deletion/publication, shared infrastructure | The relevant package and `PS-OPS-001`; Candidate/Launch/Operate/Retire only when their stated trigger applies. |
| Writer or manager transfer | `MANAGER_SESSION_HANDOFF.md`; pushed SHA, relinquishment, and `--intent transfer` before the receiver writes. |

Approved mockups remain binding. Documented non-material accessibility, truth,
focus, or reflow adaptations are allowed. Changes to composition, hierarchy,
dominant action, color, type, or responsive interaction return to ChatGPT and
the owner. Require homepage parity only for a current claim about changed
product.

## Review and release

- The writer does one complete-diff self-review and corrects findings.
- Independent review is required for a Protected change when the package calls
  for it, an unmitigated high-risk boundary changes, or the owner asks. It is
  not a default second implementation pass.
- Use focused tests first. Run wider checks when shared behavior, package scope,
  or a failure signal makes them useful.
- For runtime releases: PR -> required pipeline -> truthful smoke of the
  affected route/contract. Add rollback evidence for protected operations.
- Candidate is for Protected change classes; Launch for a new/broader audience;
  Operate for an actually released service; Retire for shutdown or destructive
  removal. None blocks unrelated Routine or Bounded work.

## Evidence and closeout

Use `docs/templates/OWNER_TECHNICAL_COMPLETION_REPORT.md` once. Core evidence
is outcome, branch/base/final SHA, changed paths, verification, release state,
and an honest limit/next step. Add only triggered protected evidence. Update
`CURRENT_BASELINE.yaml` only for current authority, ownership, holds, or
verified release facts.

### Documentation-only closeout

For governance/evidence/test-only changes that need not alter the deployed
artifact immediately, validate and merge through an Azure PR whose final
squash message contains `[skip ci]`; a PR title is insufficient. Record source
authority as merged while the deployed copy remains unchanged.
Do not restart App Service merely to publish bookkeeping. Do not queue a
same-SHA fallback while the automatic run is active. Run the normal pipeline
for runtime-consumed docs or changes to code, configuration, dependencies,
packaging, or deployment.

For a non-production `direction_authority` lane, use the executable grant ->
merge -> close lifecycle. Grant binds a pre-existing Pete decision, reviewed
SHA, and evidence and may not append authority. Merge allows non-overlapping
later control changes. Close proves the package tree is on current main,
removes mutation authority, and archives the lane.

An implementation candidate may use that lifecycle only when validator code
registers its exact package, branch, SHA, review, PR/CI, and scope. Pete's grant
may add merge and the sole `release_allowed_for` entry for the named dark
deployment and additive migration—not enablement, configuration, later slices,
rollback, or destructive schema. Keep an older candidate unchanged; validate
from a clean current-main verifier with `--candidate-worktree <absolute-path>`
and the same Azure origin.

## Stop conditions

Stop and seek a decision only for an unclear owner, active file collision,
identity/privacy/authorization question, unsafe migration/deletion, conflict
between current authorities, or missing locked visual authority for material
visual work. An open historical audit, old package, long document, or unrelated
Conditional result is not a stop condition.
