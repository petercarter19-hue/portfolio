# PS-RESUME-PUBLIC-REFINE-001 — Implementation Sequence and Handoff

## Safe sequence

1. Fetch `origin`, confirm PS-BASELINE-001 is on main, and record the full base SHA.
2. Create the résumé branch and inspect the live page at desktop/mobile plus all reserved source and test files.
3. Record before screenshots and a concise hierarchy/default-scan diagnosis tied to the current DOM.
4. Add or update focused tests for the intended default disclosure and preserved capabilities.
5. Refine template structure and page-specific CSS first; add the minimum JavaScript needed for accessible state/focus behavior.
6. Review against multiple fixture profiles, keyboard, zoom, reduced motion, and no-JavaScript reading order.
7. Run focused tests, guardrails, the full configured suite, and a file-boundary diff review.
8. Capture after screenshots, complete the owner/technical report, commit, push, and hand ChatGPT Work the branch plus exact full SHA. Do not merge your own lane unless the manager explicitly asks.

## Stop and ask the manager when

- the requested result requires route/backend/data changes or a second dataset;
- a shared base/theme/nav file appears necessary;
- preserving meaning conflicts with the compression target;
- the existing public data appears private, incorrect, or inconsistent;
- another active branch owns a required file;
- the work expands into Interview Studio or a wholesale redesign.

## Paste-ready kickoff

> Open and follow `START_HERE.md`, then the current governance records, Bible/Roadmap/Sync Standard, the résumé source documents required by `AGENTS.md`, and every file under `docs/initiatives/PS-RESUME-PUBLIC-REFINE-001/` named by its README. You are the Claude Code public-experience writer. Confirm PS-BASELINE-001 is merged and green, fetch `origin`, and create `work/<today>-resume-public-refine` from current `origin/main`; record the full base SHA. Refine the live public résumé’s repeated hierarchy and long default scan with accessible progressive disclosure, aiming for the Roadmap’s 8–9% perceived desktop compression while preserving meaning, data, canonical route/redirects, Ask Pete AI, contact, ATS/PDF path, and Career Constellation. Stay inside the reserved files; do not touch Interview Studio, auth, database, Capture, global nav/theme, or datasets. Prove desktop/mobile/keyboard/zoom/reduced-motion behavior, keep focused and guardrail tests green, capture before/after evidence, complete the standard report, push, and hand ChatGPT Work the branch plus exact full commit SHA for review.
