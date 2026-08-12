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
  directly to `main`. Preserve unrelated edits, worktrees, branches, stashes,
  artifacts, and secrets.
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
| Material visual direction or a change to a locked design | `OWNER_VISUAL_INTEGRITY_STANDARD.md`; ChatGPT is the sole creator of revised production visual authority and the owner accepts it. |
| Story composition | `OWNER_STORY_COMPOSITION_STANDARD.md`. |
| Capture, Moment, Journal, audience, or projection truth | `PS-JOURNAL-001` and its linked contract. |
| Projects | `PS-PROJECTS-001`. |
| Protected release, migration, identity/security, deletion/publication, shared infrastructure | The relevant package and `PS-OPS-001`; Candidate/Launch/Operate/Retire only when their stated trigger applies. |
| Actual writer or manager transfer | `MANAGER_SESSION_HANDOFF.md`, with pushed SHA and explicit relinquishment; record an in-place active-lane writer change through the control-only `--intent transfer` preflight before the receiver writes. |

An existing approved mockup remains binding visual authority. Non-material
accessibility, truth, focus, or reflow adaptations are allowed when documented;
a material composition, hierarchy, dominant action, color language, type, or
responsive-interaction change returns to the owner/ChatGPT visual-creation
lane. Homepage parity is required only when the homepage makes a current claim
about a materially changed product.

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
and an honest limit/next step. Add protected evidence only for the risk that
triggered it. Update `CURRENT_BASELINE.yaml` only for current authority,
ownership, scoped hold, or verified release fact; do not duplicate it in every
historical status document.

### Documentation-only closeout

When a change affects only governance/evidence/tests and does not need to alter
the deployed artifact immediately, validate the exact branch, merge it through
an Azure PR whose final squash commit message contains `[skip ci]`, and let the
files enter production with the next normal runtime release. A PR title alone
does not guarantee that Azure will copy the marker into the squash commit.
Record that source authority is merged but the deployed copy is unchanged.
Do not restart App Service merely to publish bookkeeping. Do not manually
queue a fallback while an automatic run for the same `main` SHA is active.

Run the normal pipeline when documentation is itself runtime-consumed and must
become live immediately, or when the change also affects application code,
configuration, dependencies, packaging, or deployment behavior.

For a non-production `direction_authority` lane, use the executable grant ->
merge -> close lifecycle. Grant references a pre-existing Pete decision and
binds the exact pushed/reviewed SHA plus review evidence; it may not append
authority. Merge tolerates only non-overlapping control changes that entered
main after review. Close proves the exact package tree is on current main,
removes every authority-list entry, and archives the immutable lane record.
This lifecycle is unavailable to implementation or production-capable lanes.
When the candidate predates the control repair, keep its reviewed SHA and
worktree unchanged. Run the current `origin/main` script from a distinct clean
verifier with `--intent merge --fetch --require-clean --candidate-worktree
<absolute-path>`. Both paths must be registered worktrees in one Git common
directory with the same Azure origin; the candidate stays clean on its
recorded branch and tip.

## Stop conditions

Stop and seek a decision only for an unclear owner, active file collision,
identity/privacy/authorization question, unsafe migration/deletion, conflict
between current authorities, or missing locked visual authority for material
visual work. An open historical audit, old package, long document, or unrelated
Conditional result is not a stop condition.
