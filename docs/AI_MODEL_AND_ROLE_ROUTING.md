# PeerSlate AI Model and Role Routing

**Operational standard:** September 5, 2026

This is the central authority for model versions and stable delivery roles.
Packages name roles, not model versions. Verify the available model and resolved
alias before each major package, at each quarterly audit, and whenever
the active surface changes; availability, limits, and aliases can change without
changing this delivery policy.

## Lean operating model

PeerSlate uses one pass for each distinct responsibility:

```text
architect only when architecture is needed
        ↓
one sole writer implements, tests, and self-reviews the complete diff
        ↓
one fresh independent reviewer only for a defined risk trigger
        ↓
the same writer corrects accepted findings and refreshes evidence
        ↓
Pete gives final visual acceptance on the corrected build when material visual work applies
        ↓
Azure PR, pipeline, live verification, and compact closeout
```

Do not ask another model to recreate accepted architecture, repeat a complete
technical audit, or run a documentation-only deployment. When architecture is
accepted, do not send it to another premium model to recreate it. A model switch
alone does not establish independent review.

## Stable role rules

- Every package activated or transferred under this rule names exactly one
  package manager and one active writer. A package already active on 2026-08-16
  records its manager at its next handoff. The manager owns product decisions,
  scope, sequencing, shared-governance reservations, custody and routing of
  locked visual authority, conflict resolution, and final scope/product
  readiness.
- The architect is used only for new or materially changed architecture. Preserve
  its accepted package; a second architect is an escalation, not normal process.
- The writer owns implementation, complete-diff self-review, corrections, tests,
  evidence, PR readiness, and approved release/closeout.
- A fresh independent reviewer is review-only. It challenges the exact package,
  diff, SHA, and evidence; it does not receive an open-ended redesign brief.
- The original writer fixes accepted findings. Recheck only an unresolved or
  conditional finding unless the correction changes risk or architecture.
- Pete is the final visual reviewer for material user-facing work and reviews the
  corrected real build. The manager does not repeat the technical audit.
- Handoffs use repository artifacts, branch, exact full SHA, evidence, known
  gaps, and forbidden scope—not a chat transcript.
- A governance-only package may assign its manager as sole writer when no second
  writer is active; it still receives complete-diff review and applicable tests.

## Package manager and specialist routing

PeerSlate has two management levels. The overall site-audit manager owns the
global package map, dependency order, status, and dispatch. It does not
automatically manage each package. Each active package names exactly one package
manager when it is activated or transferred; an older active package does so at
its next handoff. The manager owns that bounded package through one truthful
package-exit record.
Selection is based on the package outcome and evidence needed, not vendor
preference.

| Primary outcome or evidence | Default package manager | Use when |
|---|---|---|
| Member experience and product readiness | **Codex or ChatGPT Work, according to available tools** | Choose the environment that can inspect the repository, authorized browser session, rendered states and supporting evidence needed by the package. Existing tools and useful continuity decide the assignment; a product package does not require a host transfer when its current manager can do the work. |
| Repository and technical truth | **Codex** | The primary work is repository evidence, code, tests, security, schema, backend, protected operations, Azure PR/pipeline truth, or release reconciliation. Codex may manage a bounded technical package directly. |
| Explicit Claude planning coordination | **Claude Co-Work** | The active package expressly assigns cross-artifact planning, architecture coordination, or a Claude-centered delivery lane. Claude Co-Work management is distinct from Claude Code writing. |

Codex is the default manager when the primary outcome is repository truth,
code, tests, security, schema, backend, protected operations, or release
evidence. Claude Co-Work is selected only by an explicit active-package
assignment.

ChatGPT Work is not mandatory for every package. A Routine or simple Bounded
package may be self-managed by its sole writer when a separate manager would
only repeat the writer's review; the package still records that assignment.
Being package manager grants no repository, writer, merge, release, deployment,
credential, or production-operator authority. Codex, Cursor and Claude agents
write only when the active package separately names that writer, branch, and
mutable surface. Cursor agents may also serve as assigned independent reviewers;
the reviewer remains read-only. Cursor follows the same locked-visual-authority
rules. Models and agent environments are separate
choices: verify model availability, tools, repository access and context in the
actual environment. Azure remains authoritative; a cloud agent does not inherit
local worktrees, iCloud files, browser sessions or task continuity automatically.

Original ChatGPT is the sole creator of new or materially revised
production-intent visual authority. It works directly with Pete during visual
revisions, then returns the exact accepted artifacts and state set to the
package manager. Visual assignment does not make Original ChatGPT the package
manager, architect, writer, reviewer, or release owner. ChatGPT Work may gather
and redact current signed-in evidence, brief the visual specialist, and compare
the accepted result with the live surface; it may not originate or substitute
material visual direction.

A package may name Claude or Codex as its architect. Architecture does not grant
manager or writer authority. Specialists return their accepted artifacts and
evidence to the package manager. The package manager returns one package-exit
record to the overall site-audit manager; only a genuine cross-package or
authority conflict bypasses that normal return path.

For authenticated work, Pete alone enters passwords, MFA and verification
codes, recovery information, and other credentials; confirms which QA identity
is in use; makes material owner decisions; authorizes spending, production
actions, and irreversible identity deletion; and performs genuinely
physical-device-only actions. Those retained responsibilities do not make Pete
the routine browser operator.

### Sealed synthetic-QA credential-broker exception

The following is an exact package-specific contract, not standing authority for
a new run or another task. Reverify its current claim and action-specific owner
authority; general capability or model defaults never resume a preserved proof.

`PS-SYNTHETIC-SEALED-GRAPH-DELETION-001`, as narrowly corrected by
`PS-SYNTHETIC-SEALED-GRAPH-DELETION-CORRECTION-001`, is the complete-lifecycle
form of the narrow exception established by the two preceding sealed-broker
packages. It applies to exactly two newly generated, run-scoped, ordinary QA
customer identities under the fixed owner reference
`session:01a04348-7e3e-7a11-a443-752498be91b5/owner-authorization:2026-08-28/workshop-fg-sealed-private-proof-complete-lifecycle`.
Once a separately authorized attended operation starts, its local worker may
derive the exact live App Service/OIDC/Graph authority, generate and provision
the pair, enter the credentials, execute the 38-journey private Workshop proof,
retire both application mappings, then soft- and permanently delete those exact
two Graph users with final absence proof. The reference is compiled in; there
is no authorization, identity, credential, issuer, tenant, subject, or deletion
target prompt or argument. The command carries only safe run metadata and exact
structural confirmations.

This is not general credential or production delegation. The worker targets
only the fixed production App Service and cannot change roles, Graph grants,
configuration, licensing, billing, schema, application code, or the target. It
binds the App Service custom-domain OIDC discovery/authorization authority to
the metadata UUID-hosted principal issuer and exact `PEERSLATE_AUTH_ISSUER`
setting, with no trailing-slash tolerance. It then binds the exact tenant UUID,
Graph organization, initial `.onmicrosoft.com` tenant label, delegated
`User.Read`, `User.ReadWrite.All`, and `User.DeleteRestore.All` scopes, the
`User Administrator` role, and one unchanged token caller `oid`. Missing or
mismatched pre-existing authority is a closed refusal.

After email submission, sealed sign-in resolves a document-bound password input
handle without passing a secret, then proves the exact top-level CIAM origin.
Only then does one synchronous browser-side callback recheck that same document
and origin and write the generated password. A redirect during locator waiting
detaches or changes the handle before any secret crosses the boundary, so the
redirected page receives zero password material. The worker revalidates the
exact origin immediately before password submission; any later redirect stops
without submitting the password.

Every Workshop private/generated DOM read, write, check, click, and navigation
uses the same fail-closed principle against the exact canonical origin
`https://peerslate.com`. The evaluator binds each locator or element operation
to a current top-level document with exact HTTPS origin and no port or userinfo;
it refuses hostile owner documents, detached elements, wrong cardinality, and
redirect races. Navigation targets are checked before browser use and the
resulting page is checked afterward. Writes are performed only through a
document-bound element handle and recheck the current document after handlers.

Before either Graph POST, the worker verifies the hash-pinned disposable
Playwright closure, launches and removes a separate headed probe root, prepares
four no-capture contexts, proves the signed-out private baseline, and completes
four exact active/deleted collision reads for the generated pair. It creates
each customer once, binds every 201 subject to an operation-local time window,
random mail marker, exact identity, and ordinary-customer shape, and never
blindly retries an ambiguous mutation. A definitive rejected 4xx never enters
reconciliation for that alias. Each alias
creates one item, makes exactly two edits, proves three newest-first retained
versions and byte-exact original v1 source in all three history rows, and proves
Workshop D has the exact same-row direct `dt` value `Downstream use` and direct
`dd` value `Not used elsewhere`; a nested row cannot supply either value. The
journey map contains exactly ten approved Conditionals. Foreign update and
delete probes are among them with `neutral_denial_not_distinguishable`: the
request context cannot atomically bind its endpoint to the actor page's
canonical owner document, so the worker sends no such mutation and never treats
synthetic same-origin headers as authority. Any missing, extra, substituted,
or differently placed Conditional prevents an accepted structural result. After
archive and restore, the worker re-reads each restored active item and re-proves
the same exact three versions newest first and byte-stable original v1 source
in all three rows before deletion or an accepted result. Once both exact
customers exist, a browser-proof failure may enter bounded exact-pair
retirement and Graph-deletion containment only when cleanup equals
`BrowserCleanup(4, true)` exactly; an exception or any other returned value
blocks exact-pair SQL retirement and purge.

The partial-create path is a separate recoverable exception: before browser
cleanup it may perform one bounded reconciliation and soft-delete only exact
proven active subjects if safely needed, including an earlier independently
bound subject, while an exact subject already found in deleted items remains
unpurged. It attempts bounded direct state probes and session cleanup
independently; ambiguity remains indeterminate. It never repeats a POST, lists
unrelated identities, or purges a deleted item. Irreversible purge is forbidden
until cleanup equals `BrowserCleanup(4, true)` exactly and exact-two SQL
retirement has committed.

For an accepted result, only after the post-restore history reproof, exact item
deletion, zero active and archived item residue, repeat clean-start proof,
destruction of all four contexts, disposable runtime/module release, root
removal, and the exact `BrowserCleanup(4, true)` result does the worker call the
accepted exact-two SQL retirement core. A browser-proof failure may
independently attempt exact known application-item cleanup and, after that same
exact cleanup boundary, enter exact-pair SQL and Graph containment without
becoming accepted. The full Graph path soft-deletes
both exact objects, proves active `404` plus deleted-item `200` for both, and
only after committed exact-two SQL retirement permanently deletes both exact
deleted objects and proves four final `404` responses across the active and
deleted endpoints. Any unexpected or partial state after mutation is
`indeterminate`; the worker does not authorize blind replay. It returns only
allowlisted structural counts and closed result codes and clears its direct
sealed token, caller, routing, identity, item, and subject references. It never
retains a screenshot, trace, download, DOM, browser profile, storage state,
cookie, token, claim, network record, database row, Graph response, identity
inventory, or mutation ledger. Repository implementation and review authorize
no live run. This package's Protected control explicitly requires a fresh
GPT-5.6 Sol, Ultra exact-SHA reviewer, overriding the general OpenAI model
routing below for this package only.

The assigned browser-capable operator opens pages, navigates, clicks ordinary
controls, manages tabs and refreshes, departs to and returns from public pages,
clicks ordinary sign-out controls, performs authorized visible item creation,
editing, archive or restore, and deletion, makes privacy-safe structural
observations, and carries out routine cleanup and visible residue checks. If the
package manager lacks a browser tool, the manager routes that work to a
browser-capable executor within the same task instead of assigning it to Pete.
After Pete gives any required action-time authorization or credential input,
the operator may carry out the separately authorized action; the decision and
authorization remain Pete's.

A privacy-safe screenshot is minimized to public UI or an approved synthetic
structural state and excludes credentials, MFA or recovery values, account
identifiers, sentinel or private item content, unrelated private data, and
session material. The operator never inspects, exports, records, or persists
passwords, MFA codes, cookies, tokens, claims, authentication headers, browser
profiles, or private session files.

## Mandatory independent-review triggers

A fresh independent reviewer is required for the exact branch/SHA evidence when:

1. architecture-heavy changes;
2. authentication, session, authorization, privacy, or cross-user data;
3. schema or migration work;
4. publication, audience, or deletion behavior;
5. consequential AI behavior;
6. shared infrastructure;
7. conflicting evidence; or
8. an explicit package risk control.

Ordinary bounded work skips architecture unless it needs it and skips the
independent reviewer unless one of these triggers applies. The required
pre-merge tests, complete-diff self-review, evidence, release truth, and
rollback/stop controls remain in every applicable package.

## Capability use

Use available capabilities when they advance the authorized outcome. They add
no automatic package, review cycle, configuration change or production authority.
Follow the host's applicable tool and skill instructions; a documented feature
is not proof that it is installed, connected or active here.

| Capability | When and how to use it |
|---|---|
| Parallel agents | Delegate bounded independent research, diagnosis or review when it saves time or improves evidence. Name each deliverable and return point. Concurrent writers need approved disjoint branches, paths and domains; agents sharing a checkout cannot mutate it concurrently. |
| Browser inspection | For affected user journeys, inspect rendered states, relevant desktop/mobile sizes, keyboard behavior, errors and degraded behavior. Use authorized sessions and the privacy and visual rules above. Report unavailable evidence honestly. |
| Exact-candidate review | Freeze and identify the commit being reviewed. Use a fresh read-only reviewer when a risk, package or owner requirement applies. Changing a model or application alone is not independence; corrections require the affected evidence to be checked again. |
| Governed worktrees | Reuse the package's registered durable worktree. Agent count does not justify extra checkouts. Codex or Cursor automatic creation and cleanup cannot replace `WORKTREE_LIFECYCLE.md`; preserve custody and use its tools. |
| Continuity | Record material decisions, checkpoints and results once in exact-task continuity when available. Handoffs identify the source task, repository evidence and remaining work. Verify cross-machine imports; never transfer credentials or session-only authority. |
| Goals | Create a tracked goal only when Pete explicitly requests one. Give it a bounded outcome and observable completion criteria; use a token budget only when requested. A goal does not authorize a new package or additional operations. |
| Scheduling | Schedule later or recurring work only when Pete requests it. Define the trigger, evidence, useful output and action boundary. Start monitoring with a read-only change digest; a schedule grants no production or cleanup authority. |
| Verification and stopping | Run required gates and focused behavioral checks proportional to the change. Broaden or repeat for changed inputs, failures or unresolved requirements. Stop when the authorized outcome and required checks are complete; do not add tests that merely restate the implementation or policy. |

Continue independent work while awaiting a clarification; wait for answers that
control a consequential decision. Incorporate owner corrections without losing
the original outcome. Do not repeat an approval already supplied within its
scope. Before adding an artifact, package or review pass, identify the unresolved
requirement it closes; if there is none, do not add it. After three materially
identical failures, stop retrying and report the blocker.

## Current OpenAI model routing

| Stable role | Current choice | Use |
|---|---|---|
| Architect | **GPT-6 Astra** | New or materially changed architecture; increase effort for difficult tradeoffs |
| Implementer | **GPT-6 Astra** | Repository implementation, tests, documentation, corrections and closeout; start with moderate effort and use less for focused work |
| Independent reviewer | **Fresh GPT-6 Astra, High** | Exact-SHA, risk-triggered review and audit findings; use deeper effort when the risk needs it |

These are defaults, not a compulsory model hierarchy. Sol remains optional when
actual availability, responsiveness or measured total effort supports it. Compare
accepted outcomes, corrections, elapsed time and observed usage, including
delegated work; neither cheaper tokens nor a benchmark proves lower PeerSlate
task cost. Do not run duplicate implementations solely to fill model roles.

Use the lowest reasoning effort that meets the task's evidence standard. Reserve
Max for difficult reasoning and Ultra for substantial work with useful parallel
parts; full capability use does not mean maximum effort on every task. A package
that explicitly pins a model or review control keeps that requirement within
its exact authorized scope. If it is unavailable, report the conflict rather
than silently weakening it. Otherwise use an available capable option and state
any material limitation. This policy changes no host settings or PeerSlate's
runtime AI models.

Capability references: [OpenAI model guidance](https://developers.openai.com/api/docs/guides/latest-model),
[Codex models and effort](https://learn.chatgpt.com/docs/models),
[Cursor rules and AGENTS.md](https://cursor.com/docs/rules), and
[Cursor Azure DevOps integration](https://cursor.com/docs/integrations/azure-devops).
Recheck changing availability and pricing when a decision depends on them.

## Current Claude routing

| Stable role | Current choice | Use |
|---|---|---|
| Architect | **Claude Fable 5** | New or materially changed product, data, privacy, or technical architecture |
| Implementer | **Claude Sonnet 5** | Bounded Claude Code implementation, tests, documentation, corrections, and closeout |
| Independent reviewer | **Claude Opus 5** | Exact-SHA, risk-triggered review and audit findings; version set by the owner decision recorded in PS-SLATE-STUDIO-IA-001 doc 16 §5 (2026-08-01) |

In Claude Code, confirm the resolved model with `/model` and `/status` before a
major package or audit. Do not treat a remembered marketing nickname or an
`opusplan` alias as evidence that the required role is active.

## Delivery routes

### Architecture or high-risk package

1. One architect creates or updates the durable package only where architecture
   is needed.
2. The manager confirms the bounded scope and visual/truth authority.
3. One implementer builds, tests, self-reviews, and returns exact evidence.
4. One fresh independent reviewer addresses the defined risk question.
5. The same implementer corrects accepted findings and reruns affected evidence.
6. Pete reviews the corrected build for material visual work; the manager gives
   scope/product-readiness acceptance; then release proceeds.

### Ordinary bounded package

1. The manager supplies an accepted package and the writer confirms scope.
2. One implementer builds, tests, self-reviews, corrects findings, and returns
   evidence.
3. Add one reviewer only when a mandatory trigger applies.
4. Obtain applicable acceptance, then release and close out.

### Mechanical or governance propagation

1. One capable writer performs the bounded update and complete-diff review.
2. Run deterministic checks and the relevant guardrails.
3. Use a premium reviewer only when product meaning changes, evidence conflicts,
   or another mandatory trigger applies.
4. Do not deploy merely to record documentation.

## Audit role and reporting

The audit cadence and trigger conditions live in `docs/AI_WORKFLOW.md`. An audit
uses one fresh reviewer in the active ecosystem, exact evidence and SHAs, and a
compact ranked `Pass`, `Conditional`, or `Fail` report with owners and one next
action. It samples cross-system drift rather than replaying every implementation
review. Escalate to a deeper architect review only when an audit finding raises a
real architecture question.

## Visual workflow

```text
Original ChatGPT creates the complete production-intent visual and state set
→ Pete selects and locks one exact durable authority
→ manager records interaction, truth, and accessibility contract
→ package records whether Pete or the assigned writer/agent is the visual inspector
→ if Pete is not personally inspecting: writer reviews the exact authority,
  implements one bounded pass, renders the matching state/viewport, compares,
  records mismatches, refines, and repeats without a fixed pass limit
→ agent-run path reaches exact parity and an empty mismatch register at every
  required state/viewport
→ if Pete is personally inspecting: writer returns renders, implements Pete's
  correction directions, and records Pete's final visual decision
→ one reviewer only if a defined risk trigger applies
→ same writer corrects findings and reopens the compare-refine loop for any
  visual-affecting change when the agent-run path applies
→ Pete reviews the corrected real build for final visual acceptance
→ Azure release evidence and live verification
```

Original ChatGPT is the sole visual-creation surface for new or materially
revised PeerSlate authority. This rule covers concepts, mockups, storyboards,
responsive and state sets, style exploration, and image generation or editing.
Authorities Pete locked before 2026-07-24 remain valid until materially revised.
Codex and Claude implementers may translate the exact locked authority into
code, capture implementation screenshots, report parity, usability, truth, or
accessibility findings, and make documented non-material adaptations for
semantic structure, focus, WCAG contrast, touch targets, reduced motion,
truthful state wiring, or text reflow. Those evidence and implementation
activities are not new visual design. ChatGPT Work, Codex, Claude Chat,
Co-Work, Code, and Design may not originate or substitute the visual authority.
A change to composition, hierarchy, dominant object/action, typography family,
color language, or responsive interaction model is material and returns to
Original ChatGPT and Pete for a revised exact lock.

When implementation is based on an approved mockup, that exact mockup remains
the primary visual authority throughout delivery; neither the current build nor
implementation screenshots replace it. Record who performs the visual
inspection. When Pete is not personally performing it, the writer must run the
continuous compare-refine loop in `OWNER_VISUAL_INTEGRITY_STANDARD.md` after
every bounded pass and after every later visual-affecting change. Exact
comparable-state and comparable-viewport parity with an empty mismatch register
is required for an agent-run `Pass`; an unresolved mismatch is `Conditional` or
`Fail`. When Pete personally performs the inspection, the writer implements his
correction directions, returns updated renders, and records Pete's final visual
decision without duplicating his inspection unless asked. Functional
completion, passing tests, resemblance, time pressure, or "polish later" cannot
replace visual acceptance under either path.

A visual acceptance does not replace accessibility, truth, security/privacy, or
release checks.

## Handoff requirements

Every substantial handoff contains:

1. package, status, owner decision, manager, and sole writer;
2. authoritative base, branch, exact full SHA, and ownership status;
3. governing requirements, visual authority, truth boundary, exclusions, and
   whether a review trigger applied;
4. changed files and migration/infrastructure impact;
5. tests and exact results, evidence, and accepted deviations;
6. findings, risks, conflicts, stop controls, and next action; and
7. PR, pipeline, deployment, and live status stated separately.

## PS-AI-OPS requirements

- **PS-AI-OPS-001:** One package has one designated manager and one active
  branch writer.
- **PS-AI-OPS-002:** Architecture is authored once, only when needed, and stored
  durably.
- **PS-AI-OPS-003:** The writer self-reviews the complete diff before handoff.
- **PS-AI-OPS-004:** Independent review is risk-based, fresh, exact-SHA, and
  review-only.
- **PS-AI-OPS-005:** The same writer fixes accepted review findings and reruns
  affected evidence.
- **PS-AI-OPS-006:** Pete gives final visual acceptance for material visual work
  after corrections.
- **PS-AI-OPS-007:** Pre-merge verification, runtime pipeline, live verification,
  rollback/stop controls, and truthful status boundaries remain required.
- **PS-AI-OPS-008:** Checkpoint, readiness, full-site, and triggered audits use
  the workflow cadence and one fresh reviewer.
- **PS-AI-OPS-009:** Packages use stable role names; this document is the
  periodically verified model-version authority.
- **PS-AI-OPS-010:** Cross-vendor work is used only for a bounded independent
  risk question, never to duplicate the delivery route.
- **PS-AI-OPS-011:** Original ChatGPT is the sole creator of new or materially
  revised production-intent visual authority. Existing Pete-locked authorities
  remain valid; ChatGPT Work and implementation/review agents may compare and
  make documented non-material accessibility, truth, and reflow adaptations,
  but may not create a competing or substitute design.
- **PS-AI-OPS-012:** An approved mockup remains the primary authority throughout
  implementation and review. When Pete is not personally performing the visual
  inspection, the writer repeatedly renders, compares, records, refines, and
  rechecks without a fixed pass limit until exact parity; any later
  visual-affecting change reopens the loop. When Pete personally inspects, the
  writer implements his corrections and records his final visual decision
  without a duplicate autonomous inspection unless requested.
