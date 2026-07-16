# 10 — Release, Rollback, and Final Handoff

Status: **review branch only; release is not authorized**.

## What this package may hand off

- Photo 1-aligned Slate Board experience baseline.
- Shared PeerSlate header integration.
- Short Term, Projects, Long Term, and Work board organization.
- Semantic Board/List presentation and accessible interaction baseline.
- Honest fixture/browser-local capture, proposal, Focus, and audience-preview
  states.
- Focused and regression test evidence plus desktop/mobile screenshots.

## What must remain labeled incomplete

Authenticated owner/public separation, canonical database persistence,
cross-user isolation, real voice transcription, AI proposal execution, file
upload, collaborator presence, invitations, sharing, matching, publication,
auditing, monitoring, and production-scale performance are backend work unless
the final evidence proves otherwise.

## Review-to-release sequence

1. Push the short-lived branch to Azure DevOps `origin` with an exact SHA.
2. Peter reviews Photo 1 fidelity, all storyboard states, mobile behavior,
   accessibility, fixture labels, tests, and known issues.
3. Revise on the same exclusively owned task branch until approved.
4. Only after explicit approval, open an Azure pull request to `main`.
5. Use the repository's required squash merge and delete the task branch.
6. Run the approved Azure pipeline and verify the canonical live routes/assets.
7. Record production SHA, pipeline run, route checks, screenshots, and any
   cache/version evidence.

No direct push to `main`, GitHub deployment, bypassed review, or deployment from
an unreviewed SHA is allowed.

## Rollback

Before release, rollback is simply abandoning or revising the task branch; the
production route remains unchanged. After an approved release:

- revert the squash commit through a new Azure-reviewed rollback branch/PR;
- redeploy the last known-good Azure `main` artifact if the pipeline supports
  immutable artifact selection;
- disable any separately introduced feature flag without deleting private
  records;
- verify both `/slate-board` and `/petec/slate-board`, the shared header,
  responsive navigation, and adjacent Interview Studio routes;
- do not erase browser-local or canonical user data as a visual rollback step.

Schema rollback is out of scope because PS-BOARD-001 must not add migrations.
Any later data package must supply its own tested downgrade or documented
forward-fix strategy.

## Final report fields

Branch, full SHA, base SHA, PR, Azure pipeline run, changed files, tests,
screenshots, exact live URLs, fixture-only behavior, backend deferrals, known
issues, rollback reference, and Peter's approval decision.
