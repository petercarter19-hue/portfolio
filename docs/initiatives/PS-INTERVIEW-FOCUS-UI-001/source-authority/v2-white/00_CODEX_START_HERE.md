# 00 — Codex Start Here

## Mission

Implement the approved **Interview Focus Stage** UI refactor on the existing PeerSlate Interview Studio.

The user problem is specific:

- the active question is too easy to lose because it sits too high in a long page;
- the optional dictation control and submission action are too far from the typed-answer context;
- too many future or supporting sections are visible simultaneously;
- the current background and visual weight make the page feel busier than the workflow actually is.

The product flow itself is approved and must remain intact.

## Required outcome

When Interview Me is active, a user should immediately understand:

1. what question they are answering;
2. where to type or speak;
3. what will happen when they submit;
4. what is local versus sent to PeerSlate;
5. what the next action is.

The active question, **type-first** answer composer, optional dictation control, save status, and coaching action must read as **one operating surface**.

## Mandatory repository startup procedure

Before modifying any file:

1. Read the repository root `START_HERE.md`, every applicable `AGENTS.md`, current governance pointers, active initiative registry, design authority, testing instructions, and deployment instructions.
2. Confirm the operational source of truth. PeerSlate governance has historically treated Azure DevOps `origin/main` as authoritative and GitHub as a mirror; verify the current repository instructions rather than assuming.
3. Inspect without changing anything:
   - current branch and exact SHA;
   - `git status --short --branch`;
   - `git remote -v`;
   - `git branch -vv`;
   - `git worktree list`;
   - `git stash list`;
   - untracked files;
   - existing active branches or initiatives touching Interview Studio or shared site-shell files;
   - current test status before the change.
4. Do not clean, reset, stash, switch, overwrite, or reuse another task's worktree.
5. Create a dedicated feature worktree/branch from the verified current authority using the repository's naming convention. A proposed name is:
   `work/2026-07-28-ps-interview-focus-ui-001`
6. Confirm single-writer ownership for any shared Interview Studio templates, scripts, styles, or shell files.

## Mandatory code discovery

Map the real implementation before proposing edits:

- public Interview Studio route(s), query parameters, deep links, and history route;
- route handlers and templates;
- shared global header and secondary navigation implementation;
- Interview Studio-specific CSS and theme tokens;
- Interview Me state variables and DOM sections;
- session setup and question-queue logic;
- custom/new question behavior;
- textarea source of truth and autosave lifecycle;
- every localStorage/sessionStorage key used by Studio;
- dictation implementation, permission states, silence timeout, and transcript insertion behavior;
- coaching request endpoint, request payload, processing state, response mapping, and failure state;
- score, STAR, strengths, improvement, and relevant-history rendering;
- improve-answer request and application behavior;
- automatic browser-local history behavior;
- Interview AI modes and endpoint(s);
- Video Practice camera/microphone state, recording lifecycle, playback/discard behavior, and local-only guarantees;
- theme persistence and no-state-loss behavior;
- settings, dialogs, drawers, focus restoration, keyboard shortcut, and reduced-motion logic;
- existing unit, integration, browser, accessibility, and screenshot tests.

Create a repository-local discovery record before implementation. Do not make Pete manually identify files Codex can discover.

## Functional boundary

This is a **UI/UX refactor only**.

Allowed:

- semantic markup refinement;
- template partial/component extraction within the existing stack;
- scoped CSS/token refinement;
- rearranging existing controls and content;
- progressive disclosure of existing content;
- responsive reflow;
- accessible drawers, accordions, sticky summaries, and action docks;
- focus and status-announcement improvements;
- test and fixture additions needed to prove the refactor.

Not allowed:

- route replacement;
- backend endpoint changes;
- AI prompt, rubric, score, or response-contract changes;
- authentication or authorization changes;
- database migrations;
- new server persistence;
- new account history or cross-device synchronization;
- uploading audio or video;
- invented video analytics;
- paid-plan or entitlement work;
- Ask Slate/Ask Pete integration changes;
- global design-system replacement;
- new frontend framework, component library, package manager, or build system;
- unrelated cleanup.

## Reference priority

When sources conflict, apply this order:

1. **Current released code, tests, and truthful live behavior** control functionality.
2. **The PNG mockups in this package** control composition, hierarchy, visual relationships, and target experience.
3. **The repository's approved Concept A light / Concept C dark authority and existing PeerSlate tokens** control brand/theme truth.
4. **This written handoff** controls interaction details, responsive behavior, acceptance, and scope.
5. **Static HTML prototypes** are measurement aids only.

Never change released behavior merely to make a static prototype easier to copy.

## Stop conditions

Stop and report rather than guessing if any of these occur:

- the authoritative repository or current baseline cannot be resolved;
- another active writer owns the same files;
- the checkout is dirty and ownership is unclear;
- baseline tests fail in a way that prevents trustworthy comparison;
- a requested visual state would require a backend, auth, storage, or AI-contract change;
- local-storage keys or migration behavior cannot be safely identified;
- public and private identity boundaries are unclear;
- the current action behind a mockup label cannot be mapped to released behavior;
- the visual authority conflicts with a newer owner-approved repository decision.

## Required completion evidence

Codex's final report must include both:

### Technical record

- branch, worktree, start SHA, end SHA;
- files changed and why;
- discovered route/state/storage/endpoint map;
- confirmation that backend, database, auth, and Azure resources were not changed;
- tests and commands with results;
- screenshots at every required viewport/state;
- accessibility evidence;
- functional regression evidence;
- known limitations;
- rollback method;
- uncommitted/ignored-file status;
- PR-ready summary.

### Plain-English owner report

- what visually changed;
- what functionality stayed exactly the same;
- how the experience is now easier;
- any limitations or unresolved issue;
- exactly one recommended next step;
- anything Pete must do.

Do not merge or deploy.
