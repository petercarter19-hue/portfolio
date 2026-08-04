# Remaining workspace disposition

Captured on 2026-08-04 after the first controlled cleanup pass. Pete is the
owner of every preserved item below. No prior lane has active write, merge, or
release authority; the reset lane is the only current writer.

This is a preservation inventory, not a claim that the work is accepted,
current, merged, deployed, or safe to continue. A later disposition pass must
compare each preserved item with current `origin/main`, its initiative
authority, and its Azure pull-request evidence before assigning or deleting it.

## Summary

- Registered worktrees: 45 total: 1 reset worktree, 6 with tracked edits, 11
  with untracked material only, and 27 clean but not deletion-proven.
- Unattached local branches: 6, all preserved.
- Remote non-main branches: 32, all preserved because the reset did not find
  exact completed-PR source proof sufficient for deletion.
- Four clean worktrees contain ignored local `instance/` data and remain
  preserved: `deploy-static-diagnosis`, `migration-path`,
  `portfolio-community-continuation-001`, and `portfolio-plat-000`.
- The responsive-audit and mockup-authority tips did not equal the completed
  pull-request source tips checked during cleanup, so they remain preserved.
- No force removal, reset, stash, or deletion of ambiguous material occurred.

## Registered worktrees

| Worktree | Branch | Exact HEAD | Disposition |
|---|---|---|---|
| `C:/Users/peter/Documents/portfolio` | `main` | `af1c6a2216bdb5cddd932fbc3d5c1d0e23ef95b3` | preserve: current session entry, 10 untracked roots |
| `C:/Users/peter/.codex/worktrees/c86c/portfolio` | `work/2026-07-28-api-foundation-gate-0-001` | `bd96ee1d23e0e1198fb98f02c1f80f19d7b928f4` | preserve: clean, proof pending |
| `C:/Users/peter/.codex/worktrees/e87a/portfolio` | `(detached)` | `3cfb9a2a817d78ce98c1de55806dc1dfb6f51e63` | preserve: clean, proof pending |
| `C:/Users/peter/.codex/worktrees/workshop-six-frame-architecture-20260726/portfolio` | `codex/2026-07-26-workshop-six-frame-architecture` | `ca5ef31eedc9521f27314a32b11ee493644cca29` | preserve: clean, proof pending |
| `C:/Users/peter/.codex/worktrees/workshop-visual-functional-20260725/portfolio` | `codex/2026-07-25-workshop-visual-lock-package` | `52128a57c81969788c9dde68636d26c0ebd6a7db` | preserve: tracked edits |
| `C:/Users/peter/.codex/worktrees/workshop-visual-lock-20260726/portfolio` | `codex/2026-07-26-workshop-visual-lock-architecture` | `845742f140e1689264adbdfcc4e7a51bbba7dc49` | preserve: tracked edits |
| `C:/Users/peter/Documents/portfolio/.wt/dark-theme-off` | `work/2026-08-03-disable-dark-theme` | `6766b8038942d883d54552038e48fe4893cb94b3` | preserve: untracked material |
| `C:/Users/peter/Documents/portfolio/.wt/deploy-static-diagnosis` | `work/2026-08-04-release-truth-manual-deploy-gate` | `df0010309a5c8100d8934c67633aee207bc04005` | preserve: clean plus ignored local data |
| `C:/Users/peter/Documents/portfolio/.wt/handoff-write` | `work/2026-08-04-oppslate-codex-handoff` | `48121d185bd7b640f9388ac20b18a7cd45206d49` | preserve: clean, proof pending |
| `C:/Users/peter/Documents/portfolio/.wt/migration-path` | `work/2026-08-04-governed-migration-path` | `60fe33d2891307c04a389e8250bd7df013684f39` | preserve: clean plus ignored local data |
| `C:/Users/peter/Documents/portfolio/.wt/opportunity-slate-os1` | `work/2026-08-02-opportunity-slate-os1` | `3a4db77b04c103812ceb39ef9678d60a6e2d1cfb` | preserve: untracked material |
| `C:/Users/peter/Documents/portfolio/.wt/oppslate-os2` | `work/2026-08-03-opportunity-slate-os2` | `95d184e2846023bbf0134af43911ae6a3d1b4a15` | preserve: untracked material |
| `C:/Users/peter/Documents/portfolio/.wt/oppslate-os2-gate` | `work/2026-08-04-oppslate-os2-sql-gate` | `b8c46768d5c111af50276aba6c29c6b1693aa28c` | preserve: clean, proof pending |
| `C:/Users/peter/Documents/portfolio/.wt/oppslate-os2-prod` | `work/2026-08-04-oppslate-os2-prod-record` | `597c46d21a28215aa345555e42470b1637eaead4` | preserve: clean, proof pending |
| `C:/Users/peter/Documents/portfolio/.wt/oppslate-os3` | `work/2026-08-04-opportunity-slate-os3` | `3ac0e9d5a5fb0a20ce1c9f70b1d73ae1ea2f02a9` | preserve: untracked material |
| `C:/Users/peter/Documents/portfolio/.wt/oppslate-os3-additive` | `work/2026-08-04-oppslate-os3-additive` | `f602c3fac9b867b12704a89850642de683c0779d` | preserve: clean, proof pending |
| `C:/Users/peter/Documents/portfolio/.wt/oppslate-os3-schema` | `work/2026-08-04-schema-revision-aware` | `af1c6a2216bdb5cddd932fbc3d5c1d0e23ef95b3` | preserve: tracked edits |
| `C:/Users/peter/Documents/portfolio/.wt/oppslate-os4` | `work/2026-08-04-opportunity-slate-os4` | `de8735ced7673685ef7909b9d4bd72490b74f0c3` | preserve: tracked edits |
| `C:/Users/peter/Documents/portfolio/.wt/oppslate-os5-dictation` | `work/2026-08-03-shared-dictation-module` | `e3850fd36cbaf68224420ba0e487ff320eb43e42` | preserve: untracked material |
| `C:/Users/peter/Documents/portfolio/.wt/oppslate-prod-migration` | `work/2026-08-03-oppslate-prod-migration-record` | `2aac790ca698fa59ba52fff9b78ba7146361e06c` | preserve: clean, proof pending |
| `C:/Users/peter/Documents/portfolio/.wt/oppslate-public-intake` | `work/2026-08-03-oppslate-public-intake-decision` | `773f8535e67512e16ce3a302eaab67a60ca86c08` | preserve: clean, proof pending |
| `C:/Users/peter/Documents/portfolio/.wt/oppslate-sql-gate` | `work/2026-08-03-oppslate-sql-gate` | `bd3ce52b3da45493ea9287007d14ab494bb19240` | preserve: clean, proof pending |
| `C:/Users/peter/Documents/portfolio/.wt/overview-live-fidelity` | `work/2026-07-28-overview-live-fidelity-closeout-001` | `052a3e4003bd60dffa8f16d40aabaca228c71638` | preserve: untracked material |
| `C:/Users/peter/Documents/portfolio/.wt/overview-work-impact-fidelity` | `work/2026-07-28-overview-work-impact-fidelity-001` | `86bc096c5cae7a34f1b0efdf173c8f65d09176b4` | preserve: untracked material |
| `C:/Users/peter/Documents/portfolio/.wt/profile-arch-v2` | `work/2026-08-03-profile-001-architecture-v2` | `69785989f04f334c604a9f0db0c7bcff9f155332` | preserve: clean, proof pending |
| `C:/Users/peter/Documents/portfolio/.wt/responsive-site-audit` | `work/2026-07-26-responsive-site-audit-001` | `1fed4c934d76a25fa2a9d6647748ef4c429f476e` | preserve: clean, PR-source mismatch |
| `C:/Users/peter/Documents/portfolio/.wt/studio-workshop-future-001` | `work/2026-07-28-studio-workshop-future-001` | `e8e9be24477d374933f860f42c5790e495e4d3a7` | preserve: clean, proof pending |
| `C:/Users/peter/Documents/portfolio/.wt/wave-a-live-fixes` | `work/2026-08-03-live-site-corrections` | `9c22c0a65226bff2210b0c5bc87f98f51a8bfc1c` | preserve: untracked material |
| `C:/Users/peter/Documents/portfolio-build-future-reconcile-20260729` | `work/2026-07-29-build-your-future-whiteboard-direction` | `38f6db7ea18fd0f0c295382c7366be3c17f64fe0` | preserve: clean, proof pending |
| `C:/Users/peter/Documents/portfolio-claude-review` | `codex/claude-review` | `0d39e07646c4e69fe237e7261448bf5517dc03e1` | preserve: untracked material |
| `C:/Users/peter/Documents/portfolio-community-continuation-001` | `work/2026-08-04-community-maintenance-off-request-path` | `e51c9c6122e4c2cd1d462b77230523f733f2fded` | preserve: clean plus ignored local data |
| `C:/Users/peter/Documents/portfolio-community-feed-direction-20260729` | `codex/2026-07-29-community-feed-direction` | `a540ebc8eccaa8ba2e739c6868cf6b2553acd675` | preserve: untracked material |
| `C:/Users/peter/Documents/portfolio-data-foundation-gate-001` | `work/2026-08-04-data-foundation-gate-001` | `9952d6427f57dc5a38679f616158497cb945eec4` | preserve: clean, proof pending |
| `C:/Users/peter/Documents/portfolio-delivery-reset-001` | `work/2026-08-04-delivery-reset-001` | `af1c6a2216bdb5cddd932fbc3d5c1d0e23ef95b3` | active reset only |
| `C:/Users/peter/Documents/portfolio-mockup-authority-rule-001` | `work/2026-07-26-mockup-authority-rule-001` | `4dc8b5a8985d6ae75615042dcc9b84507ab8dc01` | preserve: clean, PR-source mismatch |
| `C:/Users/peter/Documents/portfolio-model-routing` | `claude/2026-07-24-claude-model-routing` | `1f8205d5f4f0db1ce66dc0e9925a24a288ce887a` | preserve: clean, proof pending |
| `C:/Users/peter/Documents/portfolio-plat-000` | `work/2026-08-04-plat-000-app-users-base` | `c6585ecb31105350fd09220240fc96e8980b7cb4` | preserve: clean plus ignored local data |
| `C:/Users/peter/Documents/portfolio-profile-001` | `codex/2026-07-31-profile-001-direction` | `3e05fd38f6d5ace3236297f36bfa78ad687e8121` | preserve: clean, proof pending |
| `C:/Users/peter/Documents/portfolio-profile-implementation-001` | `work/2026-07-31-profile-001-implementation` | `b2358477d6d92cf09e8f4c39e6e1e7c8c0436ca1` | preserve: tracked edits |
| `C:/Users/peter/Documents/portfolio-profile-view-revisit` | `work/2026-08-03-profile-view-visibility-revisit` | `4cf4c9256cd0615b792720077a1b3cb706adf7a2` | preserve: clean, proof pending |
| `C:/Users/peter/Documents/portfolio-projects-reactions-direction-20260729` | `codex/2026-07-29-projects-reactions-direction` | `0b4f5473e8a649ead283f62c801b99f46aeb72c7` | preserve: clean, proof pending |
| `C:/Users/peter/Documents/portfolio-slate-studio-storyboard` | `codex/2026-07-24-slate-studio-storyboard` | `3cfb9a2a817d78ce98c1de55806dc1dfb6f51e63` | preserve: clean, proof pending |
| `C:/Users/peter/Documents/portfolio-studio-goals-backend` | `claude/2026-07-24-studio-goals-backend` | `f1afda8fc6f5688864ff6b8b6370e85f061a6f58` | preserve: clean, proof pending |
| `C:/Users/peter/Documents/portfolio-studio-slice-2-architecture` | `codex/2026-07-24-slate-studio-slice-2-architecture` | `f6c2b52763d50d0773f20294acacd8d8165e59da` | preserve: clean, proof pending |
| `C:/Users/peter/Documents/pscf` | `codex/2026-08-01-community-primary-feed-sol-ultra` | `3210e4030fae30bd45fb05f4ce8351b26c4ee3f1` | preserve: tracked edits |

## Exact preserved material state

The 17 non-clean worktrees above contain the following tracked changes or
untracked roots. This is a pathname inventory only; it does not accept the
contents or authorize a writer.

- Primary `portfolio`: untracked `.wt/`, `API/`, `` `0`].total``, six dated
  `artifacts/` roots, and `output/`.
- Workshop visual functional: tracked edits to
  `13_WORKSHOP_PAGE_PURPOSE_AND_NON_REDUNDANCY_INVENTORY.md` and the package
  `README.md`; three new package records and the new
  `visual-authority/workshop-variant-a/` tree.
- Workshop visual lock: tracked edits to the bounded implementation package,
  R2 owner lock, and locked authority requirements trace.
- Dark-theme-off: untracked `artifacts/2026-08-03-dark-theme-off/`.
- Opportunity Slate OS-1: untracked OS-1 and OS-1 visual-parity evidence.
- Opportunity Slate OS-2: untracked OS-2 visual-parity evidence.
- Opportunity Slate OS-3: untracked OS-3 evidence and `output/`.
- Opportunity Slate schema revision: tracked edits to migration `registry.json`,
  `govern_sql_migrations.py`, `migration_registry.py`, and its schema-path test.
- Opportunity Slate OS-4: tracked migration, completion/evidence, route,
  service, template, and three test-file edits.
- Opportunity Slate OS-5 dictation: untracked shared-dictation evidence.
- Overview live fidelity: untracked `output/`.
- Overview Work and Impact fidelity: untracked `output/`.
- Wave-A live fixes: untracked live-site-correction evidence.
- Claude review: untracked final-screenshot archive.
- Community feed direction: untracked visual candidates.
- Profile implementation: tracked app, baseline, package, migration-runner,
  database-service, and test edits plus new SQL, routes, services, assets,
  templates, tests, and output.
- Community primary-feed implementation (`pscf`): tracked visual manifest,
  public-pilot package, CSS, JavaScript, template, and test edits plus new
  architecture/handoff/review records, evidence, and preview script.

## Unattached local branches

| Branch | Exact tip | Disposition |
|---|---|---|
| `archive/2026-08-03-dark-theme-pre-reconcile` | `0c7ebf466953dddd18b583479f0064dc09f4b3c8` | preserve: archive evidence |
| `archive/stash-claude-notes-2026-06-29` | `8fae7759366c47f37dffc6ed1aca0d30bce258e9` | preserve: archive evidence |
| `archive/stash-vscode-tutorial-2026-06-30` | `5fcfdd42b0709e5f6070767526c62121890f6730` | preserve: archive evidence |
| `work/2026-07-25-entry-doc-corrections` | `89f2d4b88fb9ecf79d350cd50b6eceae36ddb32c` | preserve: prior primary checkpoint |
| `work/2026-08-03-flag-off-render-token-repair` | `d1a39f92cb490a96558dd2701ecc7da0654a450a` | preserve: no exact deletion proof |
| `work/2026-08-03-site-visual-parity-audit` | `64ba519b1132137e381ac75022f7d944b92b8b56` | preserve: no exact deletion proof |

## Remote non-main branches

The following 32 remote refs remain preserved. Their existence does not make
them active lanes.

| Remote branch | Exact tip |
|---|---|
| `origin/backup/2026-07-28-pre-interview-focus-ui-001-a85ffbc9` | `a85ffbc93a1def86f99db66df26702a59aff4cbc` |
| `origin/claude/2026-07-24-claude-model-routing` | `1f8205d5f4f0db1ce66dc0e9925a24a288ce887a` |
| `origin/claude/2026-07-24-studio-goals-backend` | `f1afda8fc6f5688864ff6b8b6370e85f061a6f58` |
| `origin/codex/2026-07-24-slate-studio-slice-2-architecture` | `f6c2b52763d50d0773f20294acacd8d8165e59da` |
| `origin/codex/2026-07-24-slate-studio-storyboard` | `3cfb9a2a817d78ce98c1de55806dc1dfb6f51e63` |
| `origin/codex/2026-07-26-workshop-six-frame-architecture` | `ca5ef31eedc9521f27314a32b11ee493644cca29` |
| `origin/codex/2026-07-26-workshop-visual-lock-architecture` | `845742f140e1689264adbdfcc4e7a51bbba7dc49` |
| `origin/codex/2026-07-29-projects-reactions-direction` | `0b4f5473e8a649ead283f62c801b99f46aeb72c7` |
| `origin/work/2026-07-17-member-history-completion` | `b439afb2c94b527f68d6d31ba7a9e34e3f49387d` |
| `origin/work/2026-07-21-mandatory-visual-agent-workflow` | `0dc12b52817bbabf5e110a0d36312901b1368980` |
| `origin/work/2026-07-22-journal-migration-runner-registration` | `68c2355a537061309296ebdaa6559f11035e892e` |
| `origin/work/2026-07-22-journal-query-normalization-j1x` | `e33fb7d163b30a44d6cb05a9e4faba8f593d20dd` |
| `origin/work/2026-07-22-public-connective-001` | `82f241ad47fbb66372b14ac21e2ee69110c6c1aa` |
| `origin/work/2026-07-25-entry-doc-corrections` | `89f2d4b88fb9ecf79d350cd50b6eceae36ddb32c` |
| `origin/work/2026-07-25-overview-owner-review` | `ac2f9baf98394921ade4770f69f46b38a3f1bf54` |
| `origin/work/2026-07-28-api-foundation-gate-0-001` | `bd96ee1d23e0e1198fb98f02c1f80f19d7b928f4` |
| `origin/work/2026-07-29-build-your-future-whiteboard-direction` | `38f6db7ea18fd0f0c295382c7366be3c17f64fe0` |
| `origin/work/2026-08-03-flag-off-render-token-repair` | `d1a39f92cb490a96558dd2701ecc7da0654a450a` |
| `origin/work/2026-08-03-oppslate-prod-migration-record` | `2aac790ca698fa59ba52fff9b78ba7146361e06c` |
| `origin/work/2026-08-03-oppslate-public-intake-decision` | `773f8535e67512e16ce3a302eaab67a60ca86c08` |
| `origin/work/2026-08-03-oppslate-sql-gate` | `bd3ce52b3da45493ea9287007d14ab494bb19240` |
| `origin/work/2026-08-03-profile-001-architecture-v2` | `69785989f04f334c604a9f0db0c7bcff9f155332` |
| `origin/work/2026-08-03-profile-view-visibility-revisit` | `4cf4c9256cd0615b792720077a1b3cb706adf7a2` |
| `origin/work/2026-08-03-site-visual-parity-audit` | `64ba519b1132137e381ac75022f7d944b92b8b56` |
| `origin/work/2026-08-04-community-maintenance-off-request-path` | `e51c9c6122e4c2cd1d462b77230523f733f2fded` |
| `origin/work/2026-08-04-data-foundation-gate-001` | `9952d6427f57dc5a38679f616158497cb945eec4` |
| `origin/work/2026-08-04-opportunity-slate-os3` | `3ac0e9d5a5fb0a20ce1c9f70b1d73ae1ea2f02a9` |
| `origin/work/2026-08-04-opportunity-slate-os4` | `de8735ced7673685ef7909b9d4bd72490b74f0c3` |
| `origin/work/2026-08-04-oppslate-codex-handoff` | `48121d185bd7b640f9388ac20b18a7cd45206d49` |
| `origin/work/2026-08-04-oppslate-os2-prod-record` | `597c46d21a28215aa345555e42470b1637eaead4` |
| `origin/work/2026-08-04-oppslate-os2-sql-gate` | `b8c46768d5c111af50276aba6c29c6b1693aa28c` |
| `origin/work/2026-08-04-oppslate-os3-additive` | `f602c3fac9b867b12704a89850642de683c0779d` |

## Restart rule

Do not reopen one of these items by entering its worktree and saying "continue."
First select the owner outcome, verify whether the old checkpoint is still
useful against current main, name one manager and one writer, reserve exact
surfaces in `CURRENT_LANES.json`, and run the delivery preflight. When old work
is useful, port the bounded result into a fresh worktree from current main;
do not turn the old checkout into the new source of truth.
