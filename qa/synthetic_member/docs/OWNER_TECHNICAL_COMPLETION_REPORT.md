# Owner technical completion report

Package: `PS-SYNTHETIC-MULTI-MEMBER-QA-001`

State: local implementation candidate repaired after independent review;
exact-candidate re-review pending;
registry, live identities, attended deployed proof, merge, deployment,
enablement, and production acceptance remain unperformed.

## Outcome

The candidate provides a reusable provider-free foundation for two neutral
member aliases, clean and switching client journeys, bidirectional isolation
checks, minimized evidence, and fail-closed cleanup accounting.

It does not create or access an identity, open a browser, make a network or
database request, operate a session, delete application data, or prove deployed
two-member behavior.

## Source and custody

- Base: Azure `origin/main`
  `445fbab35fc0789c5ed298a2c1eabab56edf5308`
- Branch: `work/2026-08-20-synthetic-multi-member-qa-001`
- Activation: Azure PR 558, build 1341, merged control commit
  `445fbab35fc0789c5ed298a2c1eabab56edf5308`
- Frozen implementation SHA: the exact commit containing this report, supplied
  separately in the independent-review handoff
- Writer: the dedicated Codex package-manager task
- Reviewer: fresh independent reviewer assigned; first review required changes

## Changed surfaces

- `qa/synthetic_member/`
- `scripts/run_synthetic_member_qa.py`
- `tests/synthetic_member_qa/`

The candidate does not edit application runtime, authentication, route, SQL,
pipeline, configuration, environment, dependency, feature, template, or static
asset files.

`docs/governance/PACKAGE_REGISTRY.json` remains unchanged because the active
Interview AI lane owns that exact shared path. Documentation stays beside the
QA module until that collision clears. Package-registry tests pass because no
unregistered `docs/initiatives` directory is introduced.

## Built result

- Exactly `member_a` and `member_b` are retained; no external identity inventory
  exists in the candidate.
- The canonical matrix has 38 journeys covering clean clients, signed-out
  baseline, distinct arrival, simultaneous use, list/read/update/delete/export
  and forged-reference denial both ways, local storage, switches both ways,
  refresh, tabs, public return, sign-out, cross-tab sign-out, expiry, and repeat
  start.
- Evidence has an exact JSON shape and no free-text detail field.
- Email, URL, UUID, token-shaped, identity, session, private-record, and
  screenshot fields or values are refused.
- Pass, Conditional, Fail, cleanup, and final result are calculated rather than
  trusted from stored claims.
- Safety failures cannot be downgraded to Conditional, and deployed evidence
  requires a valid timestamp plus recorded release and browser version.
- Each alias must create at least one item before final evidence can Pass.
- Parser refusals do not echo supplied values, and initialization refuses to
  overwrite an existing evidence destination.
- Zero active residue and destruction of all four contexts are required for
  Pass; unknown retention cannot become Pass.
- The CLI performs local JSON plan and evidence operations only.

## Verification

Pass:

- 29 focused synthetic-member contract and CLI tests;
- 58 existing auth and sign-in/member-arrival tests;
- 12 existing Interview Studio storage-isolation tests;
- 42 package-registry, governance-pointer, and site-rule tests;
- repository evidence-duplicate policy;
- Python compilation and Git whitespace validation; and
- command-line plan generation with all 38 canonical journeys.

The full local Windows suite ran 3,918 tests. It first identified one
package-specific registry failure and four unrelated platform failures. The
registry failure was corrected by moving the unregistered package documents
beside the QA module, and its focused invariant now passes. The other four
failures—three Community maintenance deadline/sweep cases and one POSIX file-mode
case—reproduce unchanged in the pre-candidate activation worktree on Windows.
They are not in this package's writable surfaces. A later Azure candidate CI run
is the appropriate Linux-wide confirmation; no such run or PR is authorized by
this completion state.

No live identity, provider, production database, production browser, or network
evidence was used.

## Self-review

The complete candidate diff is limited to the three recorded implementation
surfaces. The implementation has no browser-driver, HTTP-client, Azure identity,
or MSAL import. It retains counts and closed outcome codes only, keeps temporary
item handles in a redacted in-process ledger, and fails closed on missing,
extra, pending, contradictory, or sensitive evidence.

Known limitations remain explicit:

- the package registry entry is deferred because of the active shared-path
  collision;
- no authoritative pair of live QA identities has been proven available;
- cross-tab sign-out is a recorded existing product limitation;
- session expiry is controlled outside this repository; and
- no attended clean-client, cleanup, deployed, or production proof has run.

## Independent review reconciliation

The first independent review of
`abf3df078e239e28ae6c94a73cc980c26fd9c193` required five corrections:
safety-note severity, mandatory item creation for both aliases, deployed-proof
custody validation, non-reflective parser refusals, and no-overwrite
initialization. All five are implemented with focused regression coverage. The
repaired exact candidate must receive a fresh independent re-review before the
package can advance.

## Next gate

Verify, freeze, and push the repaired candidate, then obtain fresh independent
Protected re-review. After approval, stop for the separate registry and
live-identity proof gates. Do not infer implementation-candidate merge,
deployment, enablement, or production authority.
