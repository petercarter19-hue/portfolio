# PS-CAPTURE-002 — Implementation Sequence and Handoff

## Safe sequence

1. Fetch `origin`, confirm PS-BASELINE-001 is on main, and record the full base SHA.
2. Create the Capture branch; inspect the real PS-CAPTURE-001 migration, routes, service allowlist, template, styles, tests, and migration runner before editing.
3. Write focused failing migration/authorization/route tests for the agreed contract.
4. Implement the forward and guarded rollback migrations plus owner-scoped procedures.
5. Add only the needed allowlist entries and protected routes.
6. Add compact, accessible controls to the private Capture page. Keep archive reversible and delete deliberately confirmed.
7. Run focused tests, migration up/down/reapply evidence, the full suite, and diff/file-boundary review.
8. Complete the owner/technical report, commit, push, and hand back the exact branch and full SHA to ChatGPT Work. Do not merge your own lane unless the manager explicitly asks.

## Stop and ask the manager when

- the production schema differs from the migration baseline;
- safe deletion is blocked by an unknown foreign key or downstream copy;
- the existing identity boundary cannot provide the user key safely;
- another active branch owns a required file;
- implementation would require public templates, global theme/navigation, auth rewrite, Moment, placement, Journal, or account-wide export/deletion;
- rollback cannot be made honest without a product/data decision.

## Paste-ready kickoff

> Open and follow `START_HERE.md`, then the current governance records, Bible/Roadmap/Sync Standard, and `docs/initiatives/PS-CAPTURE-002/README.md` plus every document it requires. You are the ChatGPT Codex backend writer. Confirm PS-BASELINE-001 is merged and green, fetch `origin`, and create `work/<today>-capture-002` from current `origin/main`; record the full base SHA. Implement only the private Capture lifecycle package exactly as controlled: immutable original body, versioned correction, archive/restore, explicit delete, versioned per-capture JSON export, owner-derived authorization, optimistic concurrency, migration plus guarded rollback, and negative two-owner/no-auto-publish evidence. Stay inside the reserved files and exclusions. Close with the standard completion report, push the branch, and hand ChatGPT Work the branch plus exact full commit SHA for review.
