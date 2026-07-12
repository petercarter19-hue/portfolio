# Azure DevOps Deployment Runbook

## Current publishing rule

Until Peter explicitly says that GitHub Actions are fixed, **do not use GitHub Actions for deployment**. GitHub Actions are disabled for this project.

The temporary publishing path is Azure DevOps:

- Azure DevOps organization: `https://dev.azure.com/peerslate19`
- Azure DevOps project: `portfolio-site`
- Azure Git remote name: `azure`
- Production branch: `main`
- Azure Web App: `peerslate-pete`

GitHub remains a code-hosting mirror; it is not the deployment trigger during this period.

## Safe release flow

1. Confirm the user explicitly wants the change published. Do not deploy merely because a local page works.
2. Inspect `git status`, current branch, and recent commits. Preserve unrelated work.
3. Push the reviewed branch to Azure DevOps, for example:

   ```powershell
   git push azure HEAD:refs/heads/<branch-name>
   ```

4. In Azure DevOps Repos, create a pull request:

   - source: `<branch-name>`
   - target: `main`

5. Review and complete the Azure DevOps pull request. Do not push directly to `main`.
6. Confirm Azure DevOps `main` contains the resulting merge commit.
7. Check the Azure DevOps pipeline and wait for a successful deployment before calling the release live.
8. Verify the actual public URL with `curl.exe` and a browser. For the redesigned résumé, use:

   ```powershell
   curl.exe -sS -L -o NUL -w "HTTP=%{http_code} final=%{url_effective}`n" https://peerslate.com/petec/resume2
   ```

## Current Azure DevOps setup

The Azure DevOps pipeline is now configured in `azure-pipelines.yml` and is connected to the `peerslate-pete` Azure Web App through a secure Azure DevOps service connection. It:

- triggers when Azure DevOps `main` changes;
- builds with Python 3.12 and `requirements.txt`;
- deploys the application package to `peerslate-pete`;
- keeps credentials in Azure/Azure DevOps rather than Git.

Pipeline run `#20260712.1` was the first manual deployment run, started from merge commit `5962db4` (Azure DevOps PR #2). Its status must be checked before saying the site is live.

## Instructions for Claude on another computer

1. Pull from the Azure remote before doing release work:

   ```powershell
   git fetch azure --prune
   git switch main
   git pull azure main
   ```

2. Make ordinary changes on a named branch, commit them, and push that branch to `azure`.
3. Create and complete an Azure DevOps pull request into Azure `main`.
4. Open Azure DevOps **Pipelines** and verify the matching run has green **Build** and **Deploy** stages.
5. Verify the actual public page with `curl.exe` before reporting success.
6. If a pipeline pauses for an Azure DevOps environment permission, permit the existing `peerslate-pete` environment. Do not create or expose secrets.

## Do not do these things

- Do not instruct Peter to use the GitHub Actions tab or **Run workflow** while this workaround is active.
- Do not claim a completed Azure DevOps pull request is a live deployment without a successful pipeline and public URL check.
- Do not put API keys, Azure publish profiles, tokens, or passwords in files, commits, chat, or pipeline YAML.
- Do not deploy from an unreviewed or dirty branch.
