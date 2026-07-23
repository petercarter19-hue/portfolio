# Community + Journal + Owner Home milestone integration architecture contract

Date: 2026-07-22

Package: `PS-COMMUNITY-JOURNAL-HOME-MILESTONE-001`

Status: Binding architecture for implementation; no product integration has
occurred on this package branch

Release authority: Azure DevOps `origin` only

## 1. Decision and authority

Pete explicitly authorized one combined Community, Journal J1, and Owner Home
milestone package on 2026-07-22. Under `DOCUMENT_CONTROL.md`, that current owner
decision outranks the older session handoff's stop condition against mixing
Journal and Owner Home without a newly approved package. This document is that
new package's narrow contract.

The authorization permits only:

1. integrating the three exact owner-approved Azure source tips below;
2. composing their shared `templates/base.html` behavior without changing the
   approved product contracts;
3. producing exact-integration-SHA tests and evidence; and
4. routing the resulting unchanged milestone SHA through review, three Sol
   Ultra audits, and the later Azure PR gate.

It does not authorize new capability, redesign, changed copy, changed routes,
feature activation, SQL execution, deployment, production verification, or
shared-governance edits. The older governance text remains historically true
for work outside this specifically approved package and is not rewritten here.

The governing product references remain:

- PeerSlate Bible v2.8 and Roadmap v2.7 at the hashes pinned by
  `docs/governance/CURRENT_BASELINE.yaml`;
- `docs/governance/OWNER_VISUAL_INTEGRITY_STANDARD.md`;
- `docs/governance/OWNER_STORY_COMPOSITION_STANDARD.md` where applicable;
- the Community package authority map and completion report at its fixed source
  SHA;
- Journal `PS-JOURNAL-001`, including document 15's identical-bar requirements,
  accepted mockups, J1 brief, and visual-finish completion report at its fixed
  source SHA; and
- Owner Home's accepted interface mockup, nine-object finite contract,
  frontend-architecture package, intersections contract, activation brief, and
  completion report at its fixed source SHA.

If an older package-local status line conflicts with Pete's 2026-07-22 handoff,
the handoff controls only the stated fact that all three source packages have
received Pete's visual/product approval. It does not waive exact-SHA or
integration evidence requirements.

## 2. Frozen inputs and branch boundary

The architecture branch was created from the fetched Azure main tip below.
Terra must fetch Azure again immediately before integration and stop if any
source remote no longer equals its frozen SHA.

| Role | Azure ref | Frozen SHA | Relationship observed on 2026-07-22 |
| --- | --- | --- | --- |
| Integration base | `origin/main` | `e1272220f539f41810698855341b9399b14ebd73` | Exact branch creation base |
| Community | `origin/work/2026-07-21-community-tabs-impl` | `a8c04964a5a363d47a56829da01c9a5bfefe3653` | Merge base `d573b23d78eba1b398bb52952e695fe595d12d7b` |
| Journal J1 | `origin/work/2026-07-21-journal-frontend-j1-impl` | `099e8e1582c05d3e13fd54dacfeb03700f90ae09` | Merge base `d573b23d78eba1b398bb52952e695fe595d12d7b` |
| Owner Home | `origin/work/2026-07-21-home-frontend-001-impl` | `f8c882633f6e442a4f661b67f8d3c799a66a1989` | Merge base `d2592f08056e09629a302966b47fa8ff92517d8e` |

The only authorized implementation branch is
`work/2026-07-22-community-journal-home-milestone-integration`. One Terra High
writer owns it at a time. GitHub is a backup/review mirror and must not move
ahead of Azure.

## 3. Product invariants

The integration must preserve the following behavior without reinterpretation.

### Community

- Community has exactly two views: Feed and The Break.
- There is no Saved surface. A legacy Saved route may redirect to Feed only as
  already implemented by the frozen source.
- Existing Community navigation, focus behavior, responsive layouts, dark
  theme, routes, fixtures, and truth labels remain unchanged.

### Journal J1

- Journal remains private, owner-authorized, and default-off.
- Its accepted Timeline, Manage, Detail, Type, and Speak behavior and all doc 15
  visual-bar requirements remain unchanged, subject only to the narrow J1
  playback amendment in `J1_PLAYBACK_DECISION_2026-07-22.md`.
- Voice rows and waveforms remain honest static, disabled `Coming later`
  compositions in J1. Static visual approval did not prove playback, and this
  milestone must not add fake or client-only playback.
- Journal remains in the normal themed page shell, but private Journal routes
  exclude the profile tabs, Ask Pete AI header action, and floating chat action
  supplied by the global shell.

### Owner Home

- Owner Home remains a finite, private, default-off nine-object surface with the
  accepted desktop/mobile hierarchy and state behavior.
- The flag-on `/app` view uses the standalone Owner Home shell, not the public
  site sky, global header/profile navigation, footer, global chat/search/mobile
  controls, or their scripts.
- The flag-off `/app` response remains the legacy owner-workspace response,
  including its source package's exact byte-identity regression assertion.
- The standalone decision remains an explicit server-provided template value;
  it must not be inferred from a request-path substring.

### Shared safety properties

- `PEERSLATE_JOURNAL_ENABLED=false` remains the default and operational state.
- `PEERSLATE_OWNER_HOME_ENABLED=false` remains the default and operational
  state.
- Authorization, privacy, fixture truthfulness, and no-index behavior are not
  weakened.
- No source package may gain access to another package's data or actions.
- No forward or rollback migration SQL is edited or executed.
- No production behavior becomes live merely because the integration branch or
  later PR exists.

## 4. Required integration method

Terra must perform the integration from this package branch and its frozen base,
preserving source ancestry. The required order is:

1. fetch Azure and prove each remote source ref still equals its frozen SHA;
2. merge Community SHA `a8c04964a5a363d47a56829da01c9a5bfefe3653`;
3. merge Journal SHA `099e8e1582c05d3e13fd54dacfeb03700f90ae09`;
4. merge Owner Home SHA `f8c882633f6e442a4f661b67f8d3c799a66a1989`;
5. resolve the shared shell exactly as specified in section 5; and
6. add only milestone-local tests, evidence, manifests, and completion records
   required to prove the integrated result.

Use explicit no-fast-forward merges of the exact SHA objects. Do not rebase,
squash, cherry-pick selected product commits, or substitute a newer branch tip.
Those operations would weaken the proof that every reviewed source tip is an
ancestor of the milestone. At the candidate SHA, each of the frozen base and
three frozen source SHAs must satisfy `git merge-base --is-ancestor`.

The expected cross-package product overlap is `templates/base.html`. Any other
merge conflict or unexpected overlapping product edit is a stop condition:
Terra records it and returns it to the designated session manager before
resolving it. The complete candidate diff must be the union of the three frozen
source diffs plus this architecture package, the single specified shared-shell
composition, and milestone-local verification artifacts. Opportunistic cleanup
is prohibited.

If `origin/main` advances after this architecture branch's frozen base, do not
silently update the package. The manager must decide whether to integrate the
new main commit. Incorporating it produces a new candidate SHA and requires all
downstream exact-SHA checks and audits to run against that new SHA.

## 5. Binding `templates/base.html` composition

The final shared template must preserve both source packages' control signals:

- `standalone_owner_shell`, supplied explicitly by the Owner Home route; and
- `is_private_journal_path`, derived from `/app/journal` for the Journal shell
  exclusions.

The Owner Home outer shell branches remain authoritative. Journal's exclusions
are applied inside the non-standalone global-shell branches. The resulting
matrix is:

| Context | `standalone_owner_shell` | `is_private_journal_path` | Required result |
| --- | ---: | ---: | --- |
| Flag-on Owner Home `/app` | true | false | Standalone Owner Home body; no public sky, global header/profile tabs, footer, chat/search/mobile controls, or global scripts |
| Flag-off `/app` | false | false | Exact legacy owner-workspace output and normal global-shell behavior |
| `/app/journal` and descendants | false | true | Normal themed body and global header, but no profile tabs, Ask Pete AI action, or floating chat action |
| Community routes | false | false | Existing Community shell unchanged; existing Pine-room conditions continue to control Ask/chat behavior |
| All other routes | false | false | Existing public/private shell behavior unchanged |

The integrated template must therefore retain:

1. Journal's request-path and `page_room` setup;
2. Owner Home's standalone viewport/body/theme behavior;
3. Owner Home's outer exclusions around public sky, global header/navigation,
   footer, global controls, and global scripts; and
4. Journal's `not is_private_journal_path` conditions on profile tabs, Ask Pete
   AI, and floating chat within the non-standalone shell.

Do not path-sniff Owner Home, make Journal standalone, remove Journal's normal
global header, broaden either condition, or reformat unrelated template
content. The source Home byte-identity test for flag-off `/app` must pass. The
composition must also prove that Community and representative unrelated routes
remain inert to both new signals.

## 6. Allowed and forbidden changes

Allowed after the source merges:

- the exact shared-template composition in section 5;
- narrowly targeted integration regression tests for the shell matrix, source
  ancestry, flags, and evidence manifests;
- new exact-SHA evidence under
  `artifacts/ps-community-journal-home-milestone-001/`; and
- package-local implementation and completion records in this directory.

Forbidden:

- edits to shared governance pointers or the active-initiatives/task-board
  records;
- edits to forward or rollback SQL, or any SQL execution;
- new services, endpoints, routes, features, product objects, copy, visual
  treatments, or data contracts beyond the frozen sources;
- changes to flag defaults or activation state;
- unrelated cleanup, dependency upgrades, deployment configuration, or
  production actions;
- overwriting or rewriting the three source packages' historical evidence; and
- a PR, merge, deployment, feature activation, or GitHub mirror advance before
  its later explicit gate.

If an integration defect cannot be corrected within the narrow shared seam or a
milestone-local regression test, route it under section 9 rather than expanding
scope.

## 7. Exact-SHA verification and evidence contract

The frozen source evidence remains historical proof of the owner-approved
packages:

| Scope | Historical source evidence | Required preserved disclosure |
| --- | --- | --- |
| Community | 15 integrated-page PNGs, 15 manifest entries, 15 unique exact hashes | Direct Break and keyboard-focused Break are deliberately distinct and retain their focus difference |
| Journal J1 | 62 captures, 62 manifest entries, 62 unique hashes | Timeline, Manage, Detail, Type, and Speak across 1440/390/320 and light/dark |
| Owner Home | 21 captures, 15 unique hashes | Exactly two disclosed duplicate groups reached through enhanced/no-JS behavioral paths |

Those source captures do not by themselves prove the combined candidate SHA.
Terra must create new milestone-scoped evidence from the final pushed candidate
SHA without altering the historical directories. The new evidence must:

- cover the complete approved source matrices for all three packages, including
  desktop, 390, 320, light, dark, lower/long content, keyboard/focus, error or
  empty states, and the documented enhanced/no-JS paths where applicable;
- include a machine-readable manifest naming the exact candidate SHA, route,
  viewport, theme, state, file type, decoded dimensions, and exact hash of every
  capture;
- validate that files advertised as PNG are true PNG streams;
- record total entries, unique exact hashes, and every permitted duplicate or
  intentionally close pair;
- compare the integrated render with its approved source capture at decoded
  pixel level where the state is deterministic; and
- treat any material visual difference as a failure requiring correction and,
  when it changes the accepted product appearance, renewed Pete approval before
  Ultra.

The final candidate must pass, at minimum:

1. the union of the Community/navigation/focus, Journal frontend/API/service,
   and Owner Home route/accessibility/migration focused suites carried by the
   source packages;
2. new shared-shell matrix tests covering the five contexts in section 5;
3. explicit default-off and authorization/privacy regression checks;
4. Community's exact Feed/The Break/no-Saved contract checks;
5. Journal keyboard, responsive, dark, status, and private-shell checks;
6. Owner Home standalone-shell, flag-off byte-identity, finite-contract,
   navigation, responsive, and accessibility checks;
7. evidence count/hash/type/dimension/duplicate assertions for all three
   milestone subdirectories;
8. repository governance/site guardrails and the complete test suite;
9. syntax or parse checks applicable to every changed Python and JavaScript
   file;
10. `git diff --check`, complete-diff review, and an explicit unexpected-file
    audit; and
11. proof that local `HEAD`, upstream Azure branch, and Azure remote branch are
    equal and that the worktree is clean.

No database or SQL execution is permitted to satisfy these checks. Expected
isolated skips must be named and reconciled; an unexplained skip, failure, stale
evidence entry, or dirty branch prevents candidacy.

## 8. Writer and review sequence

The architecture writer relinquishes branch ownership after publishing this
contract. The mandatory sequence is:

1. one Terra High writer performs the exact integration and self-review;
2. one independent Sol High reviewer reviews the complete diff, tests,
   integration evidence, shell composition, and product invariants;
3. Terra corrects every accepted finding on the same branch;
4. Sol High verifies the corrections and freezes one clean, pushed candidate
   SHA;
5. Pete reviews only if integration caused a material visual/product difference
   from an already accepted source authority; and
6. three independent, read-only Sol Ultra audits run in parallel, one each for
   Community, Journal, and Owner Home, all against that same candidate SHA.

The designated session manager coordinates ownership, verifies SHA continuity,
routes findings, and combines the three Ultra outcomes. The manager does not add
another substantive quality review after Sol Ultra.

Every Ultra auditor must inspect its complete requirements and authority,
changed files, desktop/mobile/dark evidence, visual quality and fidelity,
navigation/integration, accessibility/keyboard behavior, security/privacy,
fixture truthfulness, feature flags, tests, evidence hashes and duplicate
claims, regressions, branch cleanliness, ancestry, and local/upstream/remote
equality. Each returns `Pass`, `Conditional`, or `Fail` with specific findings.

## 9. Verdict, routing, and invalidation

The milestone verdict is `Pass` only if all three independent Ultra results are
`Pass` for the same unchanged pushed SHA. One `Conditional` makes the milestone
Conditional; one `Fail` makes it Fail. Conditional or Fail work does not enter
the PR/integration gate.

Findings route as follows:

- implementation, style, test, evidence, or visual-implementation failure:
  Terra High;
- visual implementation that diverges from accepted authority: Terra High,
  with Pete approval required if the correction changes the accepted product;
- inadequate visual authority: Sol Extra High architecture/design lane and
  Pete;
- architecture or requirements mismatch: Sol Extra High architecture; and
- material product decision: Pete.

Any code, test, or evidence change after an Ultra Pass invalidates that Pass for
the affected scope. A change to `templates/base.html`, a feature flag, shared
configuration, base synchronization, or another cross-package seam invalidates
all three Passes. A strictly package-local correction still requires a new
candidate SHA, Sol High correction verification, and a fresh Ultra audit for
the affected scope plus cross-package regression proof. If there is doubt about
scope, rerun all three.

An incorporated `origin/main` advance also creates a new candidate and
invalidates all prior candidate-SHA audits.

## 10. PR and operational boundary

After all three Ultra audits Pass the exact unchanged SHA, the milestone is
approved only for the Azure PR/integration gate. The permitted next operation is
one Azure PR from this task branch into `main`, followed by the repository's
required pipeline and squash-merge controls. Direct pushes to `main` remain
forbidden.

PR approval is not deployment approval. Merge, deployment, feature activation,
live verification, and GitHub mirror refresh remain separate gates. Both flags
stay false through this package. GitHub may be refreshed only after Azure is
again authoritative and must never move ahead of it.

## 11. Terra handoff checklist

Before writing, Terra must report and verify:

- fetched `origin/main` and all four exact frozen refs;
- clean isolated worktree on the named integration branch;
- sole writer ownership; and
- no shared-governance reservation conflict, because this package does not edit
  those files.

Before relinquishing, Terra must provide:

- final exact SHA and Azure remote equality;
- source-ancestor proof for all three frozen tips and the frozen base;
- the complete conflict/resolution record;
- complete changed-file and unexpected-file audits;
- exact focused, guardrail, full-suite, syntax, evidence, and diff-check results;
- milestone evidence path, manifest counts, hashes, and duplicate disclosures;
- confirmation that both flags remain false and no SQL, merge, deployment, or
  activation occurred; and
- a package completion report naming the independent Sol High reviewer as the
  next receiver.

Any unmet item is reported honestly as Conditional or Fail; it is not silently
waived.
