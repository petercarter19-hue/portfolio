# PeerSlate Shared AI and Git Workflow

This is the canonical operating agreement for Peter, Codex, Claude, and any other coding agent working on PeerSlate. It applies on every computer and in every worktree.

Read this file in full before making repository changes or running Git write operations. `AGENTS.md` supplies shared product and quality rules to Codex. `CLAUDE.md` supplies Claude-specific entry instructions. This file controls Git collaboration, branch ownership, handoffs, pull requests, deployment, cleanup, lean delivery, and audits. `docs/AI_MODEL_AND_ROLE_ROUTING.md` is the central model-version and stable-role authority.

If another repository document conflicts with this file about Git workflow, follow this file and report the conflict. Explicit instructions from Peter for a specific task can create an exception, but the exception must be stated and recorded in the handoff.

## Repository map

- `origin` is the Azure DevOps repository and the only authoritative remote.
- `origin/main` is the production branch and the source of truth for current code.
- `github` is the GitHub backup mirror. It is not a development or deployment source.
- GitHub Actions deployment is intentionally disabled. Do not enable it or use it to publish PeerSlate.
- Azure Pipelines is the only production deployment path.
- `archive/*` tags preserve historical or unfinished work. They are recovery references, not active development branches.
- There is no active remote named `azure`. Instructions that say to push to `azure` are obsolete.

Expected remote URLs:

```text
origin  https://dev.azure.com/peerslate19/portfolio-site/_git/portfolio-site
github  https://github.com/petercarter19-hue/portfolio.git
```

## Non-negotiable rules

1. Never commit or push directly to `main`.
2. Use one short-lived branch for each task.
3. Only one person or AI may actively write to a branch at a time.
4. Start new work from the latest `origin/main`.
5. Commit and push all intended work before handing a task to another computer or AI.
6. Every transfer to a different writer must provide the branch name and exact full commit SHA. A self-managed writer may retain ownership through implementation, self-review, approval, release, and closeout.
7. Merge through an Azure DevOps pull request using squash merge, then delete the task branch.
8. Run relevant tests and checks before requesting or completing the pull request.
9. Preserve unrelated and unfinished work. Never discard it to make a checkout look clean.
10. Never expose, read, copy, commit, or transmit credentials or secrets.
11. Do not rewrite shared history, force-push, prune objects, or perform destructive Git cleanup without a verified recovery reference and explicit justification.
12. Keep GitHub a one-way mirror of Azure. GitHub must never become an alternate production path.
13. Assigned writers self-manage their own delivery lane: implementation, complete-diff review, correction, testing, evidence, PR readiness, approved release, production verification, and closeout.
14. The package-designated session manager manages sequencing, cross-lane file ownership, shared authority, and final manager acceptance. ChatGPT Work/Codex and Claude Co-Work have equal manager authority when assigned. The manager does not routinely repeat a writer's complete technical review when the self-certification evidence is coherent.

## Lean delivery and audit policy

Owner decision, 2026-07-24: PeerSlate uses one pass for each distinct
responsibility. Remove duplicated architecture, review, closeout, and
documentation/release ceremony unless a defined risk, conflicting evidence, or
material scope change justifies more work. This policy applies equally to Codex
and Claude. It does not remove testing, authorization/privacy controls, visual
acceptance, rollback/stop controls, Azure release evidence, or honest status
boundaries.

### Delivery route

1. Confirm package scope, writable files, truth boundary, release boundary,
   acceptance evidence, and risk classification.
2. Use one architect only when the package needs new or materially changed
   architecture. Keep the accepted result in the package; do not re-architect it
   in another ecosystem.
3. One writer implements, runs applicable tests, inspects the complete diff, and
   corrects its own findings before handoff.
4. A fresh independent reviewer is mandatory only for: architecture-heavy work;
   authentication, session, authorization, privacy, or cross-user data;
   schema or migration work; publication, audience, or deletion behavior;
   consequential AI; shared infrastructure; conflicting evidence; or an explicit
   package risk control. The review is against the exact package, diff, SHA, and
   evidence; it is not a new design exercise.
5. The same writer corrects accepted findings and reruns affected evidence. Do
   not automatically repeat a full review of the corrected diff; recheck only an
   unresolved or conditional finding, or escalate when the correction changes
   the risk or architecture.
6. For material user-facing work, the writer supplies final comparison evidence
   and Pete gives final visual acceptance on the corrected real build. The
   manager accepts scope/product readiness without replaying the technical audit.
7. Complete pre-merge verification, Azure PR and squash merge, runtime pipeline,
   live verification, rollback/stop evidence, and a compact closeout. A
   documentation-only package does not deploy merely to record its closeout.

Ordinary bounded work skips the architecture track and receives independent
review only when a listed trigger applies. A model change alone is not review
independence. Packages name manager, architect when used, writer, reviewer when
triggered, and Pete's visual role when applicable; they do not duplicate model
versions from the routing document.

### Periodic audits

Each runtime slice retains its lightweight quality check: scope/risk
classification, complete-diff self-review, applicable tests, required evidence,
and honest `Pass`, `Conditional`, or `Fail` status. System-level audits sample
integration and evidence; they do not replay every prior implementation review.

| Audit | When | Minimum scope |
|---|---|---|
| Checkpoint | Every four completed runtime implementation slices or a major phase boundary, whichever comes first | Cross-slice integration, authorization/privacy, canonical truth/provenance, accessibility/visual consistency, release truth, and governance drift |
| Readiness | Before enabling a default-off feature or opening a new public, identity, data, or publication boundary | The exact enablement/boundary contract, rollback or stop control, and production readiness evidence |
| Full site | Quarterly or before a major launch or public beta | The live system's critical journeys, security/privacy boundaries, visual quality, accessibility, operational evidence, and release truth |
| Triggered | Immediately after an incident, regression, cross-user risk, unsafe migration, conflicting evidence, or `Conditional`/`Fail` result | The affected contract plus the smallest necessary upstream/downstream integration scope |

One fresh reviewer in the active ecosystem performs an audit against exact
evidence and SHAs and returns one ranked `Pass`, `Conditional`, or `Fail` report
with owners and next action. Expand only when findings require it; use a deeper
architectural review only when the audit exposes an architecture question. Audit
evidence belongs in the affected package or a dedicated audit package and does
not by itself require a deployment.

The designated manager keeps
`docs/governance/AI_DELIVERY_AUDIT_REGISTER.md` current during normal runtime
slice closeout. The register counts only completed runtime implementation slices;
documentation, architecture, audit, and activation-only work does not count.

### Audit result handling

A `Conditional` or `Fail` result from delivery self-review, independent review,
acceptance, pipeline, or live-release verification triggers the targeted audit
defined above. A `Conditional` or `Fail` from the audit itself does **not** start
another audit: the assigned owner corrects the finding and obtains one focused
recheck against the same audit scope. Escalate only when that correction changes
the architecture, risk classification, or evidence boundary. The register's
counter resets only when the checkpoint or phase-boundary audit closes `Pass`.

## Beginning every session

Inspect before changing anything:

```bash
git status --short --branch
git branch --show-current
git remote get-url origin
git remote get-url github
git log -1 --format='%H %s'
```

Confirm that `origin` is Azure and `github` is GitHub. Do not continue using a clone whose remote names are reversed or ambiguous.

Then refresh Azure references:

```bash
git fetch origin --prune
```

If the checkout contains modifications, untracked files, a stash, or an existing task branch, identify who owns that work before switching branches. Do not blindly stash, reset, overwrite, or delete it. Preserve unrelated work under a clearly named branch, stash, tag, or local archive and report what you did.

For a genuinely new task, update `main` and create a task branch:

```bash
git switch main
git pull --ff-only
git switch -c work/YYYY-MM-DD-short-task-name
```

Examples:

```text
work/2026-07-15-fix-private-feed
work/2026-07-15-fix-auth-boundary
work/2026-07-15-add-pipeline-tests
```

If a branch for that exact task already exists on Azure, fetch and continue it instead of creating a competing branch:

```bash
git fetch origin --prune
git switch --track origin/work/YYYY-MM-DD-short-task-name
```

If the branch already exists locally:

```bash
git switch work/YYYY-MM-DD-short-task-name
git pull --ff-only
```

## Working on a task

- Keep the branch limited to one coherent task.
- Make small, reviewable commits with descriptive messages.
- Inspect `git status` and `git diff` throughout the task.
- Stage specific paths instead of using `git add .` without review.
- Inspect the staged patch before committing:

```bash
git diff --cached
git status --short
```

- Do not mix screenshots, generated artifacts, local configuration, unrelated cleanup, or another agent's changes into the commit unless the task explicitly requires them.
- Add focused tests for behavior changes and run the relevant existing suite.
- If `main` moves while the task is open, fetch Azure and merge `origin/main` into the task branch when necessary. Avoid rebasing or force-pushing a branch another computer may have fetched.
- Push meaningful checkpoints so work is not stranded on one computer:

```bash
git push -u origin HEAD
```

## Self-managed delivery lanes

Owner decision, 2026-07-24: Codex and Claude may self-manage an assigned branch
from implementation through self-review and release closeout. The assigned
writer performs the work that previously required a separate manager technical
pass.

The writer must:

1. confirm the package, visual authority, release boundary, writable files, and
   shared integration zones before editing;
2. implement the bounded package and inspect the complete diff against its
   exact `origin/main` base;
3. find and correct its own regressions, missing requirements, accessibility
   failures, visual deviations, unsafe assumptions, and unrelated changes;
4. run the focused, guardrail, full-suite, migration, infrastructure,
   responsive, accessibility, and production-intent checks that the package or
   risk level requires, including a pre-merge verification gate;
5. synchronize with current `origin/main`, resolve only in-scope conflicts, and
   rerun affected evidence before requesting acceptance;
6. write the standard completion report with exact commands/results, branch,
   full SHA, screenshots, parity/deviation evidence, limitations, conflicts,
   and a self-certification result of `Pass`, `Conditional`, or `Fail`;
7. stop and report `Conditional` or `Fail` rather than hide a failed check,
   unresolved security/privacy issue, destructive migration uncertainty,
   unsupported production claim, or material design deviation; and
8. after Pete/designated-session-manager acceptance, complete its own Azure PR, pipeline,
   production verification, package-local architecture/evidence update, and
   release closeout unless the package assigns those actions elsewhere.

Self-certification is acceptable completion evidence. The designated session manager may rely on
the report and a short product/readiness acceptance review instead of rerunning the
entire implementation audit. Independent review follows the defined lean-delivery
triggers; deeper review is reserved for conflicting evidence, material scope
drift, or an architecture question exposed by evidence.

This delegation does not permit a writer to approve its own owner acceptance.
For material user-facing work, the writer performs and reports the visual
comparison; Pete gives final visual acceptance on the corrected real result and
the designated session manager accepts scope/product readiness. The acceptance
may be concise and report-based. A writer also may not use a UI
capability flag as authorization: backend access, audience, publication, and
data-lifecycle controls remain server-enforced.

Package-local requirements, architecture, decisions, evidence, and completion
reports belong on the task branch. Shared records such as `CURRENT_BASELINE.yaml`,
`CURRENT_STATE.md`, `ACTIVE_INITIATIVES.md`, the Bible, and the Roadmap may be
edited only when the package explicitly reserves them. The Bible is not a changelog:
update it only for a constitutional product decision. Use the
Roadmap for sequencing/architecture changes and the current-state records for
verified implementation and release status.

## Portable session management

Owner decision, 2026-07-19: package management is a portable role. A ChatGPT
Work/Codex manager session or Claude Co-Work may perform the same governed
manager functions when the active initiative names it:

- establish the package, gate, visual authority, branch owner, writable files,
  shared integration zones, and release boundary;
- receive and evaluate self-certified writer evidence without automatically
  repeating the full technical audit;
- coordinate truth, accessibility, feasibility, visual/product acceptance,
  Azure PR/pipeline/live verification, and package closeout;
- keep implementation, demonstration, deployment, and live-production status
  distinct; and
- escalate conflicts, evidence gaps, unsafe migrations, or owner decisions.

Each package has exactly one designated session manager at a time. Different
managers may coordinate separate packages in parallel, but they may not both
write the same branch or reserve the same shared governance files. A manager
reviewing a writer branch remains read-only unless the writer explicitly
relinquishes it with the exact branch and full SHA. Claude Co-Work management is
therefore distinct from Claude Code implementation ownership.

When management moves between sessions or tools, the outgoing manager returns
the package ID, current gate, writer branch and exact SHA, evidence status,
visual/owner decision, shared-file reservation, unresolved conflicts, and the
single next action. Chat memory is never the handoff authority; the repository
package and Azure branch are.

## Visual integrity for user-facing work

Before any user-facing design or implementation, read
`docs/governance/OWNER_VISUAL_INTEGRITY_STANDARD.md` and record the exact visual
authority in the initiative. An owner-approved production-intent demonstration,
mockup, storyboard, or walkthrough is a binding minimum: implementation must be
recognizably the same interaction model and match or exceed its hierarchy,
composition, clarity, and finish.

ChatGPT is the sole creation lane for new or materially revised PeerSlate
production-intent visual authority. It creates or revises the concept, mockup,
responsive/state set, style exploration, or image asset; Pete selects and locks
the exact durable authority. Authorities Pete locked before this 2026-07-24
decision remain valid until a material revision is needed. Codex and Claude
writers implement the authority, capture browser evidence, report mismatches,
and may make documented non-material adaptations for semantic structure, focus
visibility, WCAG contrast, touch targets, reduced motion, truthful state wiring,
or text reflow. Those adaptations do not change the dominant object/action,
composition, hierarchy, typography family, color language, or responsive
interaction model. A change to one of those visual-direction controls is
material and returns to ChatGPT and Pete for a revised exact lock. This does not
add a duplicate reviewer or visual pass.

The writer must return named desktop/mobile and applicable focus, 200% zoom,
reduced-motion, long-content, processing, failure, and recovery evidence plus a
parity/deviation summary and self-certification. Pete gives final visual
acceptance for material user-facing work on the corrected build unless explicitly
delegated. The manager confirms scope/product readiness and may rely on the
returned evidence and a focused review rather than recreating the writer's entire
visual audit. Passing tests, a clean branch, or a working happy path does not by itself
satisfy visual completion. Demonstrations must still state honestly which
behavior is live, illustrative, stored, transmitted, local-only, private,
public, or future.

Every user-facing package must also perform the homepage-product parity check
defined in the same standard. If the logged-out homepage presents, demonstrates,
or links the product, the package must identify the affected homepage section
and compare it with the accepted real product. A material change to product
function, hierarchy, theme, truth status, or visual finish requires either a
same-wave homepage update or an explicitly linked downstream parity package.
The real product releases first when sequencing is necessary, but the package
does not claim homepage parity is closed while the public projection remains
stale. Voice and Interview Studio are current examples; the rule applies to
every present and future homepage product section.

For any My Story design, schema, editor, projection, or rendering work, also
read `docs/governance/OWNER_STORY_COMPOSITION_STANDARD.md`. The member owns the
composition. Direct manipulation requires keyboard and structured equivalents;
layout metadata remains separate from canonical content; layout save and Story
publication remain separate; and an AI layout proposal is never silently
applied, saved, overwritten, or published.

## Branch ownership and AI coordination

- A branch has exactly one active writer.
- Codex and Claude may work simultaneously only on different task branches.
- Two computers may not edit the same branch simultaneously.
- Reading or reviewing another branch is allowed; modifying it requires an explicit handoff.
- The current writer must commit, push, provide the exact SHA, and state that ownership is relinquished before another writer continues.
- A self-managed writer does not relinquish its branch merely because it reached self-review or PR readiness. It may retain ownership through post-acceptance release and closeout.
- The receiving agent must fetch and verify that exact SHA before editing.
- Never infer a handoff from phrases such as "latest code" or "everything is pushed." Require the branch and SHA.

Receiving an existing branch:

```bash
git fetch origin --prune
git switch work/YYYY-MM-DD-short-task-name
git pull --ff-only
git rev-parse HEAD
git status --short --branch
```

The returned SHA must match the handoff. If it does not, stop and reconcile the discrepancy before editing.

## Required handoff format

Use this exact structure when transferring work between Peter, Codex, Claude, or computers:

```text
PeerSlate handoff

Source of truth: origin (Azure DevOps)
Branch: work/YYYY-MM-DD-short-task-name
HEAD: <full 40-character commit SHA>
Base: origin/main at <full 40-character commit SHA>
Working tree: clean | list every remaining file
Pushed to Azure: yes | no
Commits included: <short list>
Tests/checks: <commands and results>
Files/areas changed: <summary>
Visual authority/status: <named authority; parity evidence; Pete/manager acceptance>
Production status: not deployed | Azure run and verification details
Known issues or deferred work: <summary>
Next action: <single clear next step>
Active writer relinquished: yes | no
Self-certification: Pass | Conditional | Fail
Self-review evidence: <complete diff, tests, screenshots, parity, security/privacy, conflicts>
Acceptance requested: technical report | visual/product | release
```

Never claim that work is deployed merely because it is committed or pushed.

## Pull request and production deployment

1. Push the task branch to `origin`.
2. Open an Azure DevOps pull request from the task branch into `main`.
3. The self-managed writer reviews the complete diff and confirms the branch contains no unrelated work.
4. Run the relevant tests, syntax checks, and smoke checks.
5. For material user-facing work, the writer self-certifies the named visual
   authority comparison and documented deviations, resolves applicable review
   findings on the same branch, then obtains Pete's final visual acceptance on
   the corrected build and the manager's scope/product-readiness acceptance.
   Acceptance may rely on the report and focused product review; a second
   line-by-line implementation audit is not required.
6. Resolve review feedback before acceptance, rerunning affected tests and
   evidence; recheck only unresolved or conditional findings.
7. Squash-merge the pull request.
8. Delete the source branch after the merge.
9. Confirm the Azure pipeline associated with the merged `main` commit succeeds.
10. Verify the public production behavior and, when applicable, verify that production assets or a version marker correspond to the merged SHA.

Do not describe a deployment as successful until both the Azure pipeline and the public site have been verified.

Never publish through GitHub Actions. The tracked GitHub workflow is retained only as history and is disabled at the repository level.

## Finishing a task

After the Azure pull request is merged and production verification is complete:

```bash
git switch main
git fetch origin --prune
git pull --ff-only
git branch -d work/YYYY-MM-DD-short-task-name
git fetch origin --prune
```

Because a squash merge creates a new commit, Git may reject `git branch -d` even when Azure successfully merged the task. In that case, do not immediately use `-D`. Verify the completed Azure pull request against the exact local branch tip:

```bash
git fetch origin --prune
git switch main
git pull --ff-only
git rev-parse work/YYYY-MM-DD-short-task-name
az repos pr show --id <PR_ID> --query '{status:status,mergeStatus:mergeStatus,sourceCommit:lastMergeSourceCommit.commitId,mergeCommit:lastMergeCommit.commitId}' --output json
git ls-remote --heads origin refs/heads/work/YYYY-MM-DD-short-task-name
```

All of these conditions must be true:

1. The PR status is `completed`.
2. The PR merge status is `succeeded`.
3. The PR's `sourceCommit` exactly matches `git rev-parse` for the local task branch.
4. The PR records a non-empty `mergeCommit`.
5. The `ls-remote` command returns no remote task branch because Azure deleted it after merging.

Only then may the squashed local branch be removed with:

```bash
git branch -D work/YYYY-MM-DD-short-task-name
```

This narrow, PR-verified squash-cleanup case is the only routine exception to the rule against `git branch -D`. If any condition fails, preserve the branch and investigate it. Do not substitute a comparison with current `main`: later merges can legitimately change `main` after the task PR completes.

The agent that completes the release should update the GitHub mirror:

```bash
git push github main --follow-tags
```

If the GitHub push fails, report it. Do not change the source of truth, enable GitHub deployment, or force-push as a workaround. If GitHub and Azure diverge, compare them and create a recovery tag before considering any history repair.

## Worktrees

- Use a worktree only when two tasks truly need to run concurrently on the same computer.
- Each worktree must have its own task branch.
- Never attach the same branch to two worktrees.
- Name temporary worktrees clearly and report their paths.
- Remove a worktree promptly after its branch is merged or its work is safely archived.
- Do not leave detached or abandoned worktrees behind.

Different computers do not require worktrees. They require separate task branches and clear ownership.

## Shared files versus machine-local state

The following files are tracked in Git and therefore shared after commit, push, and pull:

- `AGENTS.md`
- `CLAUDE.md`
- `docs/AI_WORKFLOW.md`
- source code, tests, and tracked project documentation

The following are machine-local and are not synchronized automatically:

- Git configuration
- credentials and keychain entries
- `.env`
- virtual environments and caches
- untracked preview files
- worktrees and stashes
- the locally customized `.claude/launch.json`

`.claude/launch.json` currently contains machine-specific preview configuration on the primary Mac and is marked `skip-worktree` there. Never stage or commit its machine-specific contents. Do not assume the skip-worktree setting exists on another clone; Git index settings are local to each clone.

Before every commit, verify that no local configuration or secret is staged.

## Configuring a second computer

Do not try to repair a badly divergent clone in place. Preserve it until its local work has been reviewed, then make a fresh Azure clone:

```bash
mv portfolio portfolio-old-YYYY-MM-DD
git clone https://dev.azure.com/peerslate19/portfolio-site/_git/portfolio-site portfolio
cd portfolio
git remote add github https://github.com/petercarter19-hue/portfolio.git
git config remote.pushDefault origin
git config push.default current
git config pull.ff only
git config fetch.prune true
git config fetch.pruneTags true
git fetch origin --prune
git status --short --branch
```

Do not delete the renamed old clone until its branches, uncommitted files, worktrees, and stashes have been checked for unique work.

## Destructive operations and recovery

Normal branch creation, commits, pushes to task branches, pull requests, tests, and Azure deployments are authorized project work.

The following are not normal cleanup and require special care:

- `git reset --hard`
- `git clean -fd` or `git clean -fdx`
- `git checkout -- <path>` or equivalent discard operations
- deleting unmerged branches with `git branch -D`
- deleting stashes or dirty worktrees
- force-pushing any shared branch
- rewriting `main`
- deleting archive tags
- `git prune` or aggressive garbage collection

Before any such operation:

1. Explain why it is necessary.
2. Identify exactly what would be removed or rewritten.
3. Create and verify a recovery branch, tag, bundle, or archive.
4. Confirm the operation is limited to the intended scope.
5. Report the recovery reference afterward.

Prefer `git branch -d` after a verified merge. Do not use `-D` merely because deletion is inconvenient.

The verified squash-merge cleanup procedure in "Finishing a task" is an allowed exception because it requires Azure's completed-PR record, an exact source-tip SHA match, a successful merge commit, and a deleted remote branch.

Historical work from the July 14, 2026 consolidation is preserved under `archive/2026-07-14/*` tags, plus the earlier `archive/slate-board-v2` and `archive/chatbot-widget-mvp0` tags. Do not delete these tags without a separate preservation review.

## Completion report

Every completed task must report:

- outcome in plain English
- branch and exact commit SHA
- Azure pull request and merge status
- changed files or areas
- tests and checks run with results
- named visual authority, parity/deviation evidence, and owner/manager visual
  acceptance status for user-facing work
- working-tree status
- Azure pipeline result
- production verification result
- GitHub mirror result
- self-certification result and complete-diff review status
- designated session manager and manager-handoff status
- disclosed failures, conflicts, escalations, and evidence limitations
- remaining risks, assumptions, or follow-up work

The words "done," "deployed," "current," or "clean" must be backed by the corresponding Git, test, pipeline, and production evidence.
