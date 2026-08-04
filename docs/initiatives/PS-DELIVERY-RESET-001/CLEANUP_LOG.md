# PS-DELIVERY-RESET-001 controlled cleanup log

## Pass 1 - exact merged and contained worktrees

Executed on August 4, 2026 under Pete's explicit controlled-cleanup authority.
Every target was checked before removal for:

- an exact absolute path outside the primary and reset worktrees;
- a clean tracked and untracked Git status;
- only disposable Python or pytest cache directories when ignored files were
  present;
- an exact local branch tip equal to the successful Azure PR's
  `lastMergeSourceCommit`, or a detached commit already contained in
  `origin/main`; and
- a dated recovery ref created before removal.

No `--force`, filesystem-recursive delete, stash deletion, remote-branch
deletion, production operation, or modification of a dirty worktree was used.

### Removed

| Removed worktree | Local branch or state | Proof | Recovery ref |
|---|---|---|---|
| `C:/Users/peter/.codex/worktrees/2f5c/portfolio` | detached `0d39e07` | commit contained in `origin/main`; registration and contents removed, empty locked directory shell remains | `refs/archive/delivery-reset-2026-08-04/detached/codex-2f5c` |
| `C:/Users/peter/Documents/portfolio-public-nav-001` | detached `d357d94` | commit contained in `origin/main` | `refs/archive/delivery-reset-2026-08-04/detached/public-nav-001` |
| `portfolio/.wt/mockup-fidelity-official` | `work/2026-07-26-mockup-authority-rule-pipeline-closeout-001` | PR 183, exact source `6d8a4e6` | `refs/archive/delivery-reset-2026-08-04/work/2026-07-26-mockup-authority-rule-pipeline-closeout-001` |
| `portfolio/.wt/od2` | `work/2026-07-26-overview-owner-decisions-001` | PR 180, exact source `1084c68` | `refs/archive/delivery-reset-2026-08-04/work/2026-07-26-overview-owner-decisions-001` |
| `portfolio/.wt/overview-visual-authority` | `work/2026-07-26-overview-visual-authority-001` | PR 184, exact source `da5d33d` | `refs/archive/delivery-reset-2026-08-04/work/2026-07-26-overview-visual-authority-001` |
| `portfolio/.wt/overview-work-impact-release-closeout` | `codex/2026-07-28-overview-work-impact-release-closeout` | PR 199, exact source `c3d3ffa` | `refs/archive/delivery-reset-2026-08-04/codex/2026-07-28-overview-work-impact-release-closeout` |
| `portfolio/.wt/overview-work-impact-release-correction` | `codex/2026-07-28-overview-work-impact-release-correction` | PR 200, exact source `fdd4ae5` | `refs/archive/delivery-reset-2026-08-04/codex/2026-07-28-overview-work-impact-release-correction` |
| `portfolio/.wt/sec-edge-closeout` | `work/2026-07-28-sec-edge-closeout-001` | PR 193, exact source `5358817` | `refs/archive/delivery-reset-2026-08-04/work/2026-07-28-sec-edge-closeout-001` |
| `portfolio/.wt/sec-edge-reland` | `work/2026-07-28-sec-edge-reland-001` | PR 192, exact source `1cb3a61` | `refs/archive/delivery-reset-2026-08-04/work/2026-07-28-sec-edge-reland-001` |
| `C:/Users/peter/Documents/portfolio-candidate-admission-001` | `work/2026-07-29-candidate-admission-001` | PR 204, exact source `cdb22ac` | `refs/archive/delivery-reset-2026-08-04/work/2026-07-29-candidate-admission-001` |
| `C:/Users/peter/Documents/portfolio-candidate-admission-002` | `work/2026-07-29-candidate-admission-002` | PR 205, exact source `7044464` | `refs/archive/delivery-reset-2026-08-04/work/2026-07-29-candidate-admission-002` |
| `C:/Users/peter/Documents/portfolio-chatgpt-visual-authority` | `codex/2026-07-24-chatgpt-visual-authority` | PR 172, exact source `935688e` | `refs/archive/delivery-reset-2026-08-04/codex/2026-07-24-chatgpt-visual-authority` |
| `C:/Users/peter/Documents/portfolio-ci-gitleaks-unblock-001` | `codex/2026-08-02-gitleaks-history-fingerprint-unblock` | PR 241, exact source `623a2b6` | `refs/archive/delivery-reset-2026-08-04/codex/2026-08-02-gitleaks-history-fingerprint-unblock` |
| `C:/Users/peter/Documents/portfolio-dark-theme-release-closeout` | `work/2026-08-03-dark-theme-release-closeout` | PR 261, exact source `59f1a73` | `refs/archive/delivery-reset-2026-08-04/work/2026-08-03-dark-theme-release-closeout` |
| `C:/Users/peter/Documents/portfolio-dark-theme-temporary-disable` | `work/2026-08-03-dark-theme-temporary-disable` | PR 260, exact source `6c9a2eb` | `refs/archive/delivery-reset-2026-08-04/work/2026-08-03-dark-theme-temporary-disable` |
| `C:/Users/peter/Documents/portfolio-governance-lean-001` | `work/2026-07-31-governance-lean-evidence-correction` | PR 219, exact source `5a35855` | `refs/archive/delivery-reset-2026-08-04/work/2026-07-31-governance-lean-evidence-correction` |
| `C:/Users/peter/Documents/portfolio-lean-process-20260724` | `work/2026-07-24-lean-ai-delivery-audits` | PR 170, exact source `05b3e5a` | `refs/archive/delivery-reset-2026-08-04/work/2026-07-24-lean-ai-delivery-audits` |
| `C:/Users/peter/Documents/portfolio-materiality-001` | `codex/2026-08-01-visual-materiality-001` | PR 222, exact source `de2143d` | `refs/archive/delivery-reset-2026-08-04/codex/2026-08-01-visual-materiality-001` |
| `C:/Users/peter/Documents/portfolio-milestone-ci-fix` | `work/2026-07-23-milestone-ci-playwright-fix` | PR 162, exact source `3d49113` | `refs/archive/delivery-reset-2026-08-04/work/2026-07-23-milestone-ci-playwright-fix` |
| `C:/Users/peter/Documents/portfolio-page-purpose-markdown-governance` | `codex/2026-07-24-page-purpose-governance-closeout` | PR 174, exact source `4b21b46` | `refs/archive/delivery-reset-2026-08-04/codex/2026-07-24-page-purpose-governance-closeout` |
| `C:/Users/peter/Documents/portfolio-performance-candidate-closeout` | `work/2026-07-29-performance-candidate-closeout-001` | PR 210, exact source `34771fd` | `refs/archive/delivery-reset-2026-08-04/work/2026-07-29-performance-candidate-closeout-001` |
| `C:/Users/peter/Documents/portfolio-performance-foundation` | `work/2026-07-29-performance-foundation-001` | PR 203, exact source `39bd6d0` | `refs/archive/delivery-reset-2026-08-04/work/2026-07-29-performance-foundation-001` |
| `C:/Users/peter/Documents/portfolio-studio-slice-1` | `work/2026-07-24-slate-studio-slice-1-shell` | PR 171, exact source `09cc54d` | `refs/archive/delivery-reset-2026-08-04/work/2026-07-24-slate-studio-slice-1-shell` |
| `C:/Users/peter/Documents/portfolio-web-arch-audit` | `work/2026-07-28-revert-sec-edge-001` | PR 191, exact source `73fce9f` | `refs/archive/delivery-reset-2026-08-04/work/2026-07-28-revert-sec-edge-001` |

### Preserved by fail-safe checks

- Windows denied removal of the final empty directory shell at
  `C:/Users/peter/.codex/worktrees/2f5c/portfolio`. Git removed its worktree
  registration and contents, and the recovery ref
  `refs/archive/delivery-reset-2026-08-04/detached/codex-2f5c` exists. No force
  or filesystem delete was attempted.
- The responsive-audit and mockup-authority-rule worktree tips did not equal
  their PRs' recorded merged source SHAs, so they were excluded.
- The release-truth, governed-migration, and PLAT-000 worktrees contain ignored
  local `instance/` data, so they were excluded.
- All dirty/untracked worktrees and all current Community, Data Foundation,
  Opportunity Slate, Profile, and Workshop checkpoints remain preserved.

### Result after pass 1

- registered worktrees: 45, down from 69 (24 removed);
- local branches: 71, down from 93;
- gone-upstream local branches: 35, down from 57;
- recovery refs: 24;
- pre-existing dirty/untracked worktrees: 17, unchanged; and
- reset worktree: the only additional dirty worktree, containing this package.

Recovery refs are local Git refs. Restore a removed branch with:

```bash
git branch <new-branch-name> refs/archive/delivery-reset-2026-08-04/<saved-ref>
```

## Pass 2 - exact merged unattached branches

Twenty-one additional local branches had no attached worktree, had a deleted
upstream, and exactly matched the successful Azure PR source SHA. Each tip was
given a recovery ref before the redundant local branch name was removed:

| Local branch removed | Azure PR | Exact source |
|---|---:|---|
| `codex/2026-07-24-page-purpose-markdown-governance` | 173 | `f48ee99` |
| `work/2026-07-22-slate-studio-direction` | 168 | `1e26339` |
| `work/2026-07-24-slate-studio-governance-closeout` | 169 | `7ed7bb2` |
| `work/2026-07-25-overview-direction-001` | 178 | `96b1e20` |
| `work/2026-07-25-overview-width-amendment-001` | 179 | `c822a74` |
| `work/2026-07-26-mockup-authority-rule-closeout-001` | 182 | `7d6f76f` |
| `work/2026-07-27-overview-live-fidelity-correction-001` | 194 | `e6b4581` |
| `work/2026-07-27-web-architecture-audit-001` | 190 | `8d7952e` |
| `work/2026-07-28-ps-interview-focus-ui-001` | 201 | `da6f939` |
| `work/2026-07-28-search-quiet-preview-001` | 196 | `76301cf` |
| `work/2026-07-28-search-quiet-preview-closeout-001` | 197 | `eae83bf` |
| `work/2026-07-29-interview-local-review-001` | 206 | `728cc0d` |
| `work/2026-07-31-governance-lean-001` | 216 | `6824de7` |
| `work/2026-07-31-governance-lean-ci-fix` | 217 | `0744235` |
| `work/2026-07-31-governance-lean-release-closeout` | 218 | `d1d649a` |
| `work/2026-08-03-disarm-github-deploy-workflow` | 247 | `99f63b4` |
| `work/2026-08-03-pipeline-pr-validation-support` | 246 | `8b01df1` |
| `work/2026-08-04-f14-scoping-and-drift-detection` | 275 | `07c13fa` |
| `work/2026-08-04-oppslate-os3-schema-release` | 274 | `cb206d6` |
| `work/2026-08-04-schema-cli-order-fix` | 276 | `6374984` |
| `work/2026-08-04-schema-entra-task-fix` | 278 | `ceb7e55` |

After pass 2, 50 local branches remain, down from 93; 14 have gone
upstreams, down from 57. Forty-five recovery refs preserve every removed tip.

## Pass 3 - repair the primary session-start path

The local `main` ref was 107 commits behind `origin/main` with no unique
commits and was not checked out. Its old `be7f857` tip was preserved at
`refs/archive/delivery-reset-2026-08-04/local-main-pre-reset`, then local
`main` was fast-forwarded to `af1c6a2`.

The primary `C:/Users/peter/Documents/portfolio` worktree was tracked-clean on
`work/2026-07-25-entry-doc-corrections` at exact pushed SHA `89f2d4b`. Its ten
untracked roots were checked against `origin/main` and had no tracked-path
conflict. The branch tip was preserved at
`refs/archive/delivery-reset-2026-08-04/primary-entry-doc-corrections`, and the
primary worktree was switched to current local `main` without cleaning,
stashing, moving, or deleting any untracked content.

Result: new sessions starting in the normal primary path now read the current
lean startup instructions instead of the 107-commit-old governance files. The
primary worktree remains read-only because it contains preserved untracked
material and direct writes to `main` are prohibited.
