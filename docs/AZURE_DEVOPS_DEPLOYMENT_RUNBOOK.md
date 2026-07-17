# Azure DevOps deployment runbook

## Publishing authority

Azure DevOps is the production source of truth for PeerSlate.

- Organization: `https://dev.azure.com/peerslate19`
- Project: `portfolio-site`
- Git remote: `origin`
- Production branch: `main`
- Pipeline: `azure-pipelines.yml`
- Azure Web App: `peerslate-pete`

The `github` remote is a backup mirror. GitHub Actions deployment stays
disabled.

## Application release

1. Fetch `origin`, confirm the exact base SHA, and protect unrelated work.
2. Work on one short-lived `work/YYYY-MM-DD-task-name` branch.
3. Run the repository's focused tests, guardrails, and full suite.
4. Push the task branch to `origin` and open an Azure DevOps pull request into
   `main`.
5. Review the diff and test evidence. Never push directly to `main`.
6. Squash-merge the pull request and delete the remote task branch.
7. Confirm `origin/main` contains the resulting merge commit.
8. Wait for the pipeline run for that exact commit to complete both Build and
   Deploy successfully.
9. Verify the canonical public or protected route with `curl.exe` and a real
   browser before reporting the release live.
10. Fast-forward the GitHub backup mirror only after Azure production
    verification.

Example public-route check:

```powershell
curl.exe -sS -L -o NUL -w "HTTP=%{http_code} final=%{url_effective}`n" https://peerslate.com/petec/resume2
```

## Approved SQL migration flow

Schema migrations are review-first and migration-first. Apply an approved
migration before deploying application code that depends on it.

1. Review the forward migration, rollback guard, owner/tenant scope, defaults,
   and verification script in the pull-request branch.
2. Confirm the migration ID is explicitly allowlisted in
   `scripts/apply_sql_migrations.py`.
3. Print the plan. This command does not open the environment file or connect
   to Azure SQL:

   ```powershell
   python scripts/apply_sql_migrations.py --migration PS-CAPTURE-001
   ```

4. After Peter's explicit approval, apply and verify through the secure local
   connection configuration:

   ```powershell
   python scripts/apply_sql_migrations.py --migration PS-CAPTURE-001 --apply --verify --env-file <local-env-path>
   ```

5. Confirm the runner reports the foundation checks and the migration-specific
   verification as successful. `PS-CAPTURE-001` provisions two synthetic
   owners, proves cross-owner isolation, and rolls the synthetic data back.
6. Record the exact command form and result without copying connection strings,
   credentials, or private capture content into Git, chat, logs, or the PR.
7. If application deployment later fails, keep the backward-compatible schema
   in place unless rollback has been separately reviewed. The capture rollback
   refuses to run when member data or later dependencies exist.

Never apply every foundation migration merely to add one approved optional
migration. Never auto-apply proposed migrations from the web-app pipeline.

## Production configuration boundary

The Azure pipeline builds with Python 3.12 and `requirements.txt`, then deploys
through the existing secure Azure DevOps service connection. Secrets belong in
Azure or approved machine-local configuration, never in repository files,
pipeline YAML, screenshots, or chat.

If a pipeline pauses for an existing Azure environment permission, approve the
existing `peerslate-pete` environment. Do not create replacement credentials or
expose service-connection details.

## Prohibited release shortcuts

- Do not use GitHub Actions or the GitHub **Run workflow** control.
- Do not push directly to `main`.
- Do not call a completed pull request live without the matching successful
  Build and Deploy stages plus a public-route check.
- Do not deploy from an unreviewed branch or mix unrelated local changes into a
  release.
- Do not request, print, copy, or commit API keys, database connection strings,
  Azure publish profiles, tokens, passwords, or certificates.
