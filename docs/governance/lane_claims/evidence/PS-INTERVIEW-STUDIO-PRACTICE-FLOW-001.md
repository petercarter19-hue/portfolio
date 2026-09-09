# PS-INTERVIEW-STUDIO-PRACTICE-FLOW-001 — candidate evidence

## Scope and authority

Pete authorized this package under
`session:01a0789c-c166-7eb0-8588-517c27f13b86/pete-chat-2026-09-08/approved-interview-studio-mvp1-practice-flow`.
The package is a Protected repository change with authority through merge.
Production authority is withheld. Deployment, feature configuration, live
member proof, providers, schema, identity, storage migration, private
follow-up, onboarding, Focus/pop-out, and broader visual redesign are outside
this evidence.

## Governance lineage

- The claim-only activation merged through PR 968 at
  `5cbc9f362c184eb1d0520c6aec362de10761acf3`.
- The governed writer is
  `session:01a0839f-4e24-7d00-bbbd-333265688a81` on
  `work/2026-09-08-interview-studio-practice-flow-001` in the registered
  durable worktree.
- Exact reviewed implementation candidate:
  `1337938dffa9e2582edb41cd1e8d459ff58ca84a`.

## Candidate outcome

The candidate changes eight claimed paths. It reconciles the new Practice Flow
charter and the existing Experience Polish charter, adds the package to the
registry, and updates only the established Interview Studio template,
JavaScript, and existing tests needed for the bounded practice journey. The
registry `current_protect` count changes from 77 to 78 and total from 145 to
146.

Authenticated Interview Studio now presents one continuous question, answer,
review, optional improvement or retry, and History flow. It removes the
member-facing Finish Session ceremony, the competing authenticated completion
panel, completed-question counter, and open-session labels. Practice setup
remains optional and dismissible, with the inherited Operability focus entry,
Escape, and focus-return behavior.

An accepted review remains an immutable browser-local History record. A small
active-workspace pointer restores that sanitized record and, when present, its
bounded unsaved improvement draft through mode changes, History, and refresh.
Retry creates a later attempt instead of overwriting the accepted record.
History deletion clears matching recovery state as one guarded transaction;
unreadable, malformed, unwritable, or undeletable browser storage refuses the
operation without claiming success. Existing predecessor records are neither
deleted nor silently migrated.

The public and authenticated-flag-off markup remains byte-comparable under the
inherited regression. No application route, API payload, provider, prompt,
backend, schema, identity, feature configuration, shared visual system, or
production setting changes.

## Validation

- `tests.test_interview_studio` plus `tests.test_package_registry`: **310
  passed** (308 Interview Studio and two Package Registry tests).
- `tests.test_interview_studio_operability_browser`: **11 passed** with local,
  synthetic fixtures. The suite covers optional setup and narrow focus return,
  review/improvement restoration through all modes, History and refresh,
  immutable retry attempts, active-record deletion, and truthful preservation
  when browser-storage reads, writes, or removals fail.
- JavaScript syntax and `git diff --check`: pass.
- A broader local Windows run executed 5,647 tests and reported 11 unrelated
  environment/platform failures in Darwin/Homebrew sealed-broker behavior,
  contaminated local Playwright state, maintenance concurrency, Unix resource
  import, POSIX permissions, and lifecycle PID concurrency. It is retained as
  a limitation rather than a package failure. Protected Azure CI remains a
  required merge gate.

No live browser profile, member identity, credential, production provider, or
production destination was used in package validation.

## Independent review

Independent reviewer `agent:/root/interview_practice_flow/candidate_review`,
configured `gpt-5.6-sol` High, returned **PASS** for exact candidate
`1337938dffa9e2582edb41cd1e8d459ff58ca84a` at `2026-09-09T02:44:00Z`.

Earlier review passes found and the writer corrected four candidate issues:

- restored accepted reviews could be overwritten or resurrect a stale draft;
- browser-storage failures could falsely dismiss an improvement or start a
  retry;
- History deletion could remove the record before matching active recovery;
- unreadable storage could be mistaken for an empty store.

The final review verified the failure-distinguishing snapshots, mutation
ordering and rollback, row and detail handlers, and browser regression for
both read and removal failures. It returned no remaining finding. This review
authorizes repository merge only.

## Release truth

This evidence binds an immutable source candidate and local validation. Azure
branch policies and protected CI must pass before accepted merge. Repository
merge does not deploy, enable, or live-prove the change. Any production release
and authenticated live journey require a separate exact authorization and
release owner.
