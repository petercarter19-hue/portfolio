# PS-CI-SECRET-SCAN-ALLOWLIST-001 review evidence

Runtime-inert review-tail record for the emergency repair of the required
secret-scan build gate. Paired receipt:
`docs/governance/lane_claims/receipts/PS-CI-SECRET-SCAN-ALLOWLIST-001.json`.

- **Boundary:** Protected, independent review, repository authority
  through merge, production authority withheld. Two allowlist entries in
  `.gitleaks.toml`, plus the regression pin in
  `tests/test_operational_readiness.py` that exists to make any new
  suppression an explicit decision. No pipeline, scanner version,
  fixture, or product surface changed.

- **Why it existed:** the gate was failing on **every** branch including
  unmodified `main` (builds 2035 and 2036 on PR 783, and 2037 on plain
  main). Nothing in the repository could merge. Gitleaks' `generic-api-key`
  rule matched the SHAPE of a key-suffixed field in two unmerged work
  branches:
  `tests/fixtures/azure_startup_qualification/luna_eval_cases.json`
  (`synthetic-accessibility-v1`, `synthetic-product-v1`,
  `synthetic-delivery-v1`) and
  `tests/test_my_opportunities_qualification.py` (16 hits, 10 distinct
  shapes, e.g. `idempotency_key="revoke-1"`). No credential was involved
  in any of them and nothing leaked.

- **Why an allowlist was the only repair:** `azure-pipelines.yml` runs
  `gitleaks git .` with `fetchDepth: 0` over every fetched ref, so one
  unmerged branch breaks CI repo-wide, and editing or reverting either
  file cannot clear a finding that lives in branch history. This
  repository has hit that exact wall before: the Profile-fixtures entry
  in `.gitleaks.toml` records that "deleting the file did not and cannot
  clear the finding; only this allowlist can."

- **Delivered candidate:** `4c7e6ffb8e34bd78b0433664b6c588e0c1829e6e` on
  `work/2026-08-31-ci-secret-scan-allowlist-001`, base `310d0899` (the
  activation merge).

- **Independent review, two rounds.** Round 1 on `bbb7298b` returned
  REVISE: the second entry's trailing `now=.*$` admitted a real quoted
  credential appended after `now=`. The finding was reproduced by the
  writer before being accepted, fixed to `now=[^"']*$`, and re-verified.
  Round 2 on `4c7e6ffb` returned PASS.

- **One correction against the writer's own favour**, recorded so the
  receipt is exactly true: the review raised two adversarial cases, but
  only one was real. Scanned against a defaults-only configuration with
  no PeerSlate allowlists, gitleaks never flags a secret supplied *as*
  the `now=` value, so the old pattern was not concealing that case.
  This change closes **one** real vector, not two.

- **Verification.**
  - Full history, every fetched ref, post-fix: 2177 commits, **no leaks
    found**.
  - Negative test: non-placeholder credentials in an unrelated file are
    still detected.
  - Negative test: an unrelated secret placed *inside* an allowlisted
    file is still detected.
  - Negative test: an allowlisted line shape placed in a *different* file
    is still detected.
  - Adversarial test: a credential appended after `now=` is detected
    again under the corrected pattern.
  - An earlier negative test was discarded as invalid: it used gitleaks'
    own well-known AWS documentation placeholder, which the default
    configuration allowlists, and so proved nothing.
  - The readiness regression's assertions were replicated locally against
    the real configuration (count, path set, per-entry rule/condition/
    regexTarget/regex-list, absence of commit pinning) because worktrees
    carry no virtualenv on this machine. That replication caught a real
    writer bug: a raw-string escaping artifact that made the expected
    regex `[^"\']` instead of `[^"']`. The authoritative check remains
    the CI run.

- **Recorded deviation.** `tests/test_operational_readiness.py` is
  outside this claim's declared surfaces; `--intent write` fails with
  exactly that one error and no other. Extending the claim first was
  impossible: an extend-surfaces control transition is claim-only, so its
  branch would lack this fix and could not pass the gate being repaired.
  The owner was given both routes and selected this one over a second
  branch-policy waiver. There is no live collision -- the file is claimed
  only by a paused package, and paused claims release paths.
  **Obligation:** reconcile the claim through a proper extend-surfaces
  control transition once `main` is green, at which point that control
  PR's CI passes normally.

- **Reviewer independence disclosure.** The reviewer is the writer of
  PS-MYOPP-QUALIFICATION-001. This change unblocks that reviewer's own
  CI, and the second allowlist entry covers that reviewer's test file.
  Both review rounds tightened rather than loosened the candidate. The
  interest was disclosed to the owner, who did not reassign the review.

- **Honest limitation.** This repairs the gate; it does not address the
  underlying fragility that any single branch's test fixtures can take
  down CI for the whole repository, because the scan reads every fetched
  ref. That is a pipeline design question in `azure-pipelines.yml`, which
  this claim does not own and did not touch.

- **Not deployed.** Repository merge only. No deployment, schema, or
  production operation is claimed or performed here.
