# PS-MVP1-BROWSER-CI-001 final candidate evidence

Activation PR 972 passed Azure build 2718 and merged as
`70fe5f862f5fe27b3fd94b449abd0e23513f2406`. The active claim assigns this
Protected delivery to sole writer
`session:01a087e2-fd56-79f0-a696-6a4fc1fd44ba`; production authority is
withheld.

The original implementation candidate
`e25c146144ef61e0aaf61c08825f45c7757c586f` added one required
`InterviewStudioBrowserCI` job to the existing Build stage. It installs the
application requirements and the separate exact-pinned browser dependency
manifest, provisions the Chromium revision bound to Playwright 1.62.0, and runs
only `tests/test_interview_studio_operability_browser.py` through a fail-closed
runner. The runner pins the exact class and all 11 required method names,
reports explicit discovery, execution, pass, skip, failure and error counts,
and fails when the suite is absent, changed, empty, skipped or unsuccessful.
Ordinary optional unittest discovery remains intact.

Independent review accepted the original candidate with no findings. PR 974
then passed build 2728 and squash-merged as
`df8ee80024267888333474c4c5e4672063125af4`. Build 2728 required both
`BuildJob` and `Interview Studio browser CI`; the hosted browser log reported
11 discovered, 11 run, 11 executed, 11 passed, 0 skipped, 0 failures and 0
errors. That is historical proof for the merged original candidate, not
acceptance of the later correction.

## Owner-review correction

Owner-supplied Grok review arrived before claim close. Close PR 975 was
abandoned unmerged and its queued build canceled, so the claim remained active.
The review disposition is recorded externally with SHA-256
`ECF84D058E1D6B6A7193714278264820664878F31AD69F9D2E41D78C283B5592`.

- F1: the merged job was already wired to the strict runner, but its regression
  coverage was incomplete. The correction parses the actual Build stage,
  `InterviewStudioBrowserCI` job and step mappings. It requires the exact
  `python scripts/run_interview_browser_ci.py` command, an enabled runner, and
  fail-closed job/step settings; it rejects direct unittest substitution.
- F2: a fresh subprocess calls
  `load_selected_suite(MODULE_FILE, MODULE_NAME, CLASS_NAME, EXPECTED_METHODS)`
  against the actual existing suite. Browser startup and database reads/writes
  fail immediately if touched, exactly 11 methods must load, no tests execute,
  and the selected module cannot leak into the module cache.
- F3: the client-to-Flask review-envelope integration check remains deferred to
  a future owning package. This package does not broaden the suite or alter the
  Interview runtime/provider boundary.
- F4: the corrected candidate must repeat required Azure browser counts and
  ordinary BuildJob policy proof before merge.

Exact final reviewed candidate
`6e2d083cd898c3697c68be52cd25a7361d55263a` is one commit over merged base
`df8ee80024267888333474c4c5e4672063125af4` and changes only the already claimed
`tests/test_interview_browser_ci_runner.py`. The selected 11 browser test bodies
and every runtime file are byte-identical to the merged base.

## Verification and final independent review

- Pinned application environment: 38 focused runner and governance tests pass.
- Scoped mutation probes reject `continueOnError: true`, `enabled: false`,
  direct targeted unittest execution, and `|| true` shell fallback.
- The actual browser runner executed 11/11 selected tests with 0 skips,
  failures or errors before the final five-line assertion-only delta. The delta
  does not touch the runner or browser suite.
- `git diff --check`, claimed-path validation and write preflight pass.
- Independent reviewer
  `agent:/root/mvp_quality_package_manager/browser_ci_review` returned PASS with
  no findings on exact final candidate
  `6e2d083cd898c3697c68be52cd25a7361d55263a`. The reviewer independently
  reproduced all 38 focused tests and the four bypass probes, and confirmed the
  F2/browser-suite bytes were unchanged. Final review record SHA-256:
  `067CB3F12F1C58B388EF0D1766C9C1BDDE9A1F7FD921B60E1FF2F76191E9A17D`.

The authorized current-owner routing handoff outside the repository remains at
`outputs/CURRENT_OWNER_MODEL_ROUTING_UPDATE.md`; its post-write SHA-256 is
`52FCEAE09E809C0F9153F340E17E7E1F47D2FE190335EFEB27FCD200543E99CA`.

## Release truth

This is the immutable final-candidate record. The corrected receipt and this
evidence are the only post-review repository tail. Corrected-candidate
Azure-hosted counts, ordinary branch policies, accepted merge and formal claim
close remain the server-side closeout gates after this record.

The browser suite uses a local Flask server, synthetic Easy Auth identity
headers, patched identity lookup and intercepted provider requests. Its result
is not live identity, provider, storage, production, deployment or subjective
visual proof. Deployment remains withheld.
