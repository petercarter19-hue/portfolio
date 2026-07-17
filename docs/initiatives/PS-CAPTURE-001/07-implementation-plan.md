# Implementation plan

1. Confirm authoritative Azure base, Settings prerequisite, worktree isolation,
   product sources, and auth/data contracts. **Completed.**
2. Extend the owner blueprint with protected capture GET/POST behavior and
   deterministic validation. **Completed.**
3. Add the Capture template, owner-workspace link, and responsive accessible
   styles. **Completed.**
4. Add owner-scoped forward/rollback migrations, privacy-safe audit, and a
   transactional two-user isolation verifier. **Completed and applied.**
5. Extend the migration runner and deployment runbook for one approved optional
   migration without foundation reapplication. **Completed.**
6. Add focused route and migration-contract tests. **Completed.**
7. Run focused, guardrail, full, static, and visual validation; self-review the
   complete diff. **Completed locally and against live Azure SQL.**
8. Commit, push, and open an Azure DevOps PR with exact evidence. **Completed
   as PR 56.**
9. Apply and verify the explicitly approved migration through the secure local
   configuration. **Completed.**
10. Squash-merge, verify the exact pipeline and production route, update the
    GitHub mirror, then remove the task branch/worktree. **Application release
    completed; release-record mirror and local cleanup follow this docs update.**
