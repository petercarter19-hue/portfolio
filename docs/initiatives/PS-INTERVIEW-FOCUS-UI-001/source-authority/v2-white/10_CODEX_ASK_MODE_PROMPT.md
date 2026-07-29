# 10 — Ready-to-Paste Codex Ask Mode Prompt

Paste the block below into Codex **Ask mode** with this package available inside the repository or attached to the task.

---

You are the repository implementation planner for `PS-INTERVIEW-FOCUS-UI-001`.

This is a significant UI refactor of PeerSlate's existing Interview Studio. Start in read-only mode. Do not modify code, install packages, change configuration, create Azure resources, merge, deploy, clean worktrees, or disturb any uncommitted work.

Read, in order:

1. the repository root `START_HERE.md` and every applicable `AGENTS.md`;
2. current governance/baseline/active-initiative/design/testing instructions;
3. `docs/initiatives/PS-INTERVIEW-FOCUS-UI-001/README.md`;
4. every numbered document in that initiative folder;
5. all fourteen PNGs in `visual-authority/` at 100%;
6. the static HTML prototypes only as geometry aids.

Then inspect the actual repository and current running/local behavior. Map:

- branches/remotes/worktrees/stashes/current SHA and file ownership;
- Interview Studio routes, query parameters, deep links, handlers, templates, CSS, JavaScript, and tests;
- shared header/secondary navigation/theme implementation;
- every mode and state in Interview Me, Interview AI, Video Practice, and History;
- answer source of truth, autosave/storage keys, dictation, queue, settings, coaching request, processing, failure, review, improve, retry/next, automatic local history, theme retention, media lifecycle, and accessibility behavior;
- all endpoints and request/response contracts touched by the current frontend;
- exact likely files for each implementation phase;
- conflicts with other active initiatives or dirty/shared files.

Treat current released code/tests as functional authority and the fourteen initiative PNGs as visual authority. The approved light palette is pure white/cool-gray/navy/cobalt/teal; beige/ivory/gold artifacts are retired. Typing is the primary input and dictation is optional. This package authorizes presentation, semantic markup, responsive layout, scoped styles, accessibility, and state-visibility changes only. It does not authorize backend, endpoint, payload, AI prompt/rubric/score, storage-key, database, authentication, Azure, route, or product-semantic changes.

Produce a repository-grounded implementation plan with:

1. current-state technical map;
2. requirement-to-file map;
3. state-transition map using the actual code's names;
4. functionality preservation risks;
5. visual/component reuse plan;
6. exact phased edit plan and commit plan;
7. test and screenshot plan using the repository's existing tools;
8. stop conditions or conflicts;
9. explicit confirmation of which files should not change;
10. a `Proceed`, `Proceed with conditions`, or `Stop` recommendation.

Do not ask Pete to identify files or translate the mockups when repository inspection can answer the question. Do not write implementation code in this Ask-mode task.

---
