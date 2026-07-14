# PeerSlate Shared AI and Git Workflow

This is the canonical operating agreement for Peter, Codex, Claude, and any other coding agent working on PeerSlate. It applies on every computer and in every worktree.

Read this file in full before making repository changes or running Git write operations. `AGENTS.md` supplies shared product and quality rules to Codex. `CLAUDE.md` supplies Claude-specific entry instructions. This file controls Git collaboration, branch ownership, handoffs, pull requests, deployment, and cleanup.

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
6. Every handoff must provide the branch name and exact full commit SHA.
7. Merge through an Azure DevOps pull request using squash merge, then delete the task branch.
8. Run relevant tests and checks before requesting or completing the pull request.
9. Preserve unrelated and unfinished work. Never discard it to make a checkout look clean.
10. Never expose, read, copy, commit, or transmit credentials or secrets.
11. Do not rewrite shared history, force-push, prune objects, or perform destructive Git cleanup without a verified recovery reference and explicit justification.
12. Keep GitHub a one-way mirror of Azure. GitHub must never become an alternate production path.

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

## Branch ownership and AI coordination

- A branch has exactly one active writer.
- Codex and Claude may work simultaneously only on different task branches.
- Two computers may not edit the same branch simultaneously.
- Reading or reviewing another branch is allowed; modifying it requires an explicit handoff.
- The current writer must commit, push, provide the exact SHA, and state that ownership is relinquished before another writer continues.
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
Production status: not deployed | Azure run and verification details
Known issues or deferred work: <summary>
Next action: <single clear next step>
Active writer relinquished: yes | no
```

Never claim that work is deployed merely because it is committed or pushed.

## Pull request and production deployment

1. Push the task branch to `origin`.
2. Open an Azure DevOps pull request from the task branch into `main`.
3. Review the complete diff and confirm the branch contains no unrelated work.
4. Run the relevant tests, syntax checks, and smoke checks.
5. Resolve review feedback on the same task branch.
6. Squash-merge the pull request.
7. Delete the source branch after the merge.
8. Confirm the Azure pipeline associated with the merged `main` commit succeeds.
9. Verify the public production behavior and, when applicable, verify that production assets or a version marker correspond to the merged SHA.

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
- working-tree status
- Azure pipeline result
- production verification result
- GitHub mirror result
- remaining risks, assumptions, or follow-up work

The words "done," "deployed," "current," or "clean" must be backed by the corresponding Git, test, pipeline, and production evidence.
