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

## Current one-time setup gap

As of 2026-07-11, pull request #1 was completed into Azure DevOps `main`, but Azure DevOps Pipelines displayed **Create your first Pipeline**. That means an Azure DevOps repository and pull-request flow exist, but no Azure DevOps pipeline has yet been connected to deploy `main` to the `peerslate-pete` Azure Web App.

Do not assume that an Azure DevOps merge deploys by itself. First-time pipeline setup requires Peter's explicit approval because it creates an external deployment configuration. Configure it to:

- trigger from Azure DevOps `main`;
- build the Flask application with Python 3.12 and `requirements.txt`;
- deploy to Azure Web App `peerslate-pete`;
- keep secrets only in Azure DevOps/Azure configuration, never in Git.

After the pipeline exists, use the safe release flow above for every deployment.

## Do not do these things

- Do not instruct Peter to use the GitHub Actions tab or **Run workflow** while this workaround is active.
- Do not claim a completed Azure DevOps pull request is a live deployment without a successful pipeline and public URL check.
- Do not put API keys, Azure publish profiles, tokens, or passwords in files, commits, chat, or pipeline YAML.
- Do not deploy from an unreviewed or dirty branch.
