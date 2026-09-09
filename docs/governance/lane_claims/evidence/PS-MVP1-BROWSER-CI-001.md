# PS-MVP1-BROWSER-CI-001 candidate evidence

Activation PR 972 passed Azure build 2718 and merged as
`70fe5f862f5fe27b3fd94b449abd0e23513f2406`. The active claim assigns this
Protected delivery to sole writer
`session:01a087e2-fd56-79f0-a696-6a4fc1fd44ba`; production authority is
withheld.

Exact implementation candidate
`e25c146144ef61e0aaf61c08825f45c7757c586f` adds one required
`InterviewStudioBrowserCI` job to the existing Build stage. The job installs
the application requirements and the separate exact-pinned browser dependency
manifest, provisions the Chromium revision bound to Playwright 1.62.0, and runs
only `tests/test_interview_studio_operability_browser.py` through a bounded
runner. The runner pins the exact class and all 11 required method names,
reports explicit discovery, execution, pass, skip, failure and error counts,
and fails when the suite is absent, changed, empty, skipped or unsuccessful.
Ordinary optional unittest discovery remains intact.

The candidate changes exactly six assigned implementation files:
`azure-pipelines.yml`, `requirements-browser-ci.txt`,
`scripts/run_interview_browser_ci.py`,
`tests/test_interview_browser_ci_runner.py`,
`docs/AI_MODEL_AND_ROLE_ROUTING.md`, and
`tests/test_governance_pointers.py`. It does not change the selected Interview
suite, application/runtime behavior, visuals, identity, provider, storage,
schema or any production stage. The routing edit changes only the three current
Sol rows authorized on September 9: former Sol High assignments use Sol Extra
High and former Sol Medium assignments use Sol High. Astra routing remains
unchanged.

## Verification and independent review

- Local pinned-browser execution: 11 discovered, 11 run, 11 executed, 11
  passed, 0 skipped, 0 failures, 0 errors, 0 expected failures and 0 unexpected
  successes.
- `python -B -m unittest tests.test_interview_browser_ci_runner
  tests.test_governance_pointers -q`: 36 passed.
- The missing-suite, zero-discovery, renamed-method and skipped-method negative
  cases all failed closed. YAML parsing, required-job structure, pinned
  dependency checks, `pip check`, `git diff --check`, claimed-path validation
  and write preflight passed.
- Independent reviewer
  `agent:/root/mvp_quality_package_manager/browser_ci_review` returned PASS with
  no findings on exact candidate `e25c146144ef61e0aaf61c08825f45c7757c586f`
  and independently reproduced the 11 executed / 0 skipped browser result, 36
  focused tests and negative probes. External review record SHA-256:
  `4DDE818C12C52930FCC8FB16151FE58DCB47F5EDAC054E0390C16AEBE192B4ED`.

The authorized current-owner routing handoff outside the repository was updated
in place at `outputs/CURRENT_OWNER_MODEL_ROUTING_UPDATE.md`; its post-write
SHA-256 is
`52FCEAE09E809C0F9153F340E17E7E1F47D2FE190335EFEB27FCD200543E99CA`.

## Release truth

This is the immutable candidate-era record. The receipt and this evidence are
the only post-review repository tail. Azure-hosted required-job counts,
ordinary branch policies, accepted merge and formal claim close remain the
server-side closeout gates after this record.

The suite uses a local Flask server, synthetic Easy Auth identity headers,
patched identity lookup and intercepted provider requests. Its result is not
live identity, provider, storage, production, deployment or subjective visual
proof. Deployment remains withheld.
