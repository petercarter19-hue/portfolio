# PS-MOMENT-001 — Implementation Sequence and Handoff

## Safe sequence

1. Fetch `origin`, confirm PS-NEXT-WAVE-MANAGER-001 is on current main with a green pipeline, and record the full base SHA.
2. Create the Moment task branch and inspect PS-CAPTURE-001/002 schema, procedures, routes, service allowlist, migration runner, identity boundary, and tests.
3. Write the exact state/data/rollback design in the completion report or a package addendum before migration code. Resolve Capture-deletion propagation explicitly.
4. Add migration-contract, two-owner, source-pinning, concurrency, no-auto-publish/placement, and rollback tests before or with implementation.
5. Implement the versioned migration and verification SQL, then the minimal service/routes/protected review controls.
6. Run focused tests, Capture regressions, guardrails, the full suite, syntax checks, secret-pattern scan, `git diff --check`, and a reserved-file audit.
7. Prove forward apply → verify → guarded rollback → prior-state verification → reapply → verify against an isolated real SQL Server database with no production/member data; delete that temporary database afterward.
8. Complete the standard report, commit, push, and hand ChatGPT Work the branch plus exact full SHA. Do not run the production migration, open/complete the PR, or deploy unless the manager explicitly takes or assigns that release step.

## Stop and ask the manager when

- the existing Capture deletion contract cannot be extended without losing confirmed canonical content or retaining deleted source text;
- the work requires placement, Journal UI, public pages, profile/audience redesign, AI generation, voice/media Capture, or auth changes;
- a migration or rollback encounters unknown production dependencies;
- a required shared file is not reserved;
- another branch owns the same backend file;
- the package cannot preserve one source version and explicit confirmation without an architecture decision.

## Paste-ready kickoff

> Open and follow `START_HERE.md`, then the current governance records, Bible/Roadmap/Sync Standard, PS-CAPTURE-001, PS-CAPTURE-002, and every file named by `docs/initiatives/PS-MOMENT-001/README.md`. You are the ChatGPT Codex backend-convergence writer. Confirm PS-NEXT-WAVE-MANAGER-001 is merged and green, fetch `origin`, and create `work/<today>-moment-001` from current `origin/main`; record the full base SHA. Implement one owner-scoped text Capture source version → editable private proposal → explicit member confirmation → source-linked canonical Moment. Pin the exact source version; later Capture corrections must not silently rewrite a Moment. Preserve the source original/revisions, separate read-only source from editable proposal, keep every state private, and make confirmation deterministic and explicit. Handle Capture deletion with body-free source tombstones and safe unconfirmed/confirmed behavior. Do not publish, place, start Journal UI, add AI proposal generation, add voice/media Capture, touch public résumé/Interview Studio files, change auth/global nav/theme, or duplicate raw Capture text into downstream surfaces. Prove migration apply/verify/guarded rollback/reapply on an isolated real SQL database, two-owner denial, stale-version rejection, source pinning/deletion propagation, and no auto-publish/placement; keep focused, Capture regression, guardrail, and full tests green. Complete the standard report, push, and hand ChatGPT Work the branch plus exact full commit SHA for review; do not apply production SQL or merge without the manager release gate.
