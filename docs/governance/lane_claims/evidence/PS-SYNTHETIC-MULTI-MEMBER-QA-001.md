# PS-SYNTHETIC-MULTI-MEMBER-QA-001 completion record

- Task/package and delivery path: `PS-SYNTHETIC-MULTI-MEMBER-QA-001`, Protected.
- Outcome and member/site effect: A reusable, provider-free foundation for
  proving that two ordinary members stay distinct and private across clean
  clients, simultaneous clients, and a sequential account switch. It closes the
  tooling and evidence gap recorded as `GAP-SYNTHETIC-MULTI-MEMBER-QA`; it does
  not itself close that gap with live proof. There is no runtime, route,
  template, schema, configuration, or deployment change, so members and the
  live site are unaffected by this repository change.
- Package manager and why: `task:708d6f8b-e2d9-437d-950f-52a084e41381`, the
  recorded sole writer for this claim. Custody moved twice through governed
  transfers before the schema-v3 cutover; no implementation content changed at
  either transfer.
- Triggered specialists and return target: Independent reviewer
  `agent:synthetic-qa-independent-review-2026-08-20` returned PASS with no
  findings on the immutable candidate. Recorded in
  `lane_claims/receipts/PS-SYNTHETIC-MULTI-MEMBER-QA-001.json`.
- Branch, base SHA, final SHA, and changed paths:
  `work/2026-08-20-synthetic-multi-member-qa-001`; base
  `445fbab35fc0789c5ed298a2c1eabab56edf5308`; reviewed candidate
  `7923913049450c8c5fa1871576c71ba44233de04`. Reviewed paths are
  `qa/synthetic_member` (contracts, CLI, and package documents),
  `scripts/run_synthetic_member_qa.py`, and `tests/synthetic_member_qa`. The
  only post-review additions are this evidence file and the matching receipt.
- Verification performed and result: Re-verified on this exact candidate
  against current main: the focused contract and CLI suite passed 29 tests, and
  `plan --json` emitted the full 38-journey canonical matrix. Recorded at
  freeze: 58 existing auth and sign-in/member-arrival tests, 12 Interview
  Studio storage-isolation tests, 42 package-registry, governance-pointer and
  site-rule tests, and a full local Windows run of 3,918 tests whose only
  failures were four pre-existing Community and POSIX-file-mode cases
  reproducible on untouched main. Azure/Linux build 1346 succeeded on the
  candidate. No live identity, provider, production database, browser,
  credential, or network access was used at any point.
- Release state: Exact candidate pushed and independently reviewed. Azure PR
  560 is open, published, and merges cleanly onto current main. Azure/Linux CI
  run 1482 succeeded on the first evidence tail
  `7553a6d48ffe9c744201da5d9308b702338036c9`; the tip carrying this corrected
  record receives its own PR run, which must be green before merge. Not
  merged, not deployed, not enabled, and not live-proven.
- Known limits, deferred work, or owner decision needed:
  - Repository authority for this claim is explicitly `write_only`, so this
    package cannot admit its own merge. Expanding it to `through_merge` is
    Pete's decision and needs a `delivery-authorize` control change.
  - The package documents deliberately remain beside the module in
    `qa/synthetic_member/docs/`. `docs/initiatives/PS-SYNTHETIC-MULTI-MEMBER-QA-001`
    is reserved by the claim but intentionally left absent, because
    `tests/test_package_registry.py` requires every initiatives directory to be
    listed in `docs/governance/PACKAGE_REGISTRY.json`, and that registry path
    is claimed by no package. Creating the directory without the matching
    registry entry would fail that test on main.
  - No pair of live QA identities has been provisioned or proven available.
    Pete alone provisions or retires them and performs every login and MFA
    action; the harness never handles credentials, MFA material, cookies,
    tokens, claims, headers, browser profiles, storage state, or session files.
  - Cross-tab sign-out on `/app` is a recorded existing product limitation and
    App Service session expiry is controlled outside this repository, so those
    journeys may be Conditional and cannot be silently recorded as Pass.
  - No attended clean-client, cleanup, deployed, or production proof has run.
- Next action: Pete expands repository authority to `through_merge` on a
  `delivery-authorize` control branch. The exact merge preflight was then run
  from a clean current-main verifier against candidate
  `7923913049450c8c5fa1871576c71ba44233de04` and returned exactly one
  outstanding error, `claim does not carry repository authority through merge`;
  every other admission check passed. After the authorization merges, re-run
  that preflight, merge PR 560 once its run is green, and close the claim. The
  attended two-identity proof remains a separate, later, owner-scheduled gate.

## Protected additions

- Identity, authorization, and privacy: The retained model contains exactly the
  two neutral aliases `member_a` and `member_b`. No external identity
  inventory, secret, or personally identifying field exists in the candidate.
  Evidence has an exact JSON shape with no free-text field; email, URL, UUID,
  token-shaped, identity, session, private-record, and screenshot fields are
  refused recursively, and parser refusals do not echo supplied values.
- Fail-closed behaviour: Pass, Conditional, Fail, cleanup, and the final result
  are calculated rather than trusted from stored claims. Safety failures cannot
  be downgraded to Conditional, each alias must create at least one item, zero
  active residue and destruction of all four client contexts are required for
  Pass, and unknown retention cannot become Pass.
- Shared infrastructure or broad release: None. The tool imports no browser
  driver, HTTP client, Azure identity library, or MSAL, and cannot create an
  identity, open a site, sign in, read a session, query a database, or delete
  application data. Rollback is a repository revert of the accepted PR.
  Production authority is withheld and no production operation is included.
