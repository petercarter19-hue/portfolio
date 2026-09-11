# PS-INTERVIEW-REVIEW-HTTP-ISOLATION-001 candidate evidence

Activation PR 981 squash-merged as
`c4aa33eb5d151e8cfa20019727774a54a99cab45`. The active Bounded claim assigns
implementation to sole writer
`session:cursor-grok-interview-review-http-001`; production authority is
withheld. Required-CI wiring remains a later coordination dependency.

Exact reviewed candidate
`a9e20b0bb343fb75737e7f3bd9944af13d7edcb9` changes only:

- `tests/test_interview_review_http_browser.py`
- `tests/test_interview_review_http_browser_runner.py`

Interview production runtime, the existing eleven browser-test bodies, shared
`scripts/run_interview_browser_ci.py`, and `azure-pipelines.yml` are
byte-identical to the merged activation base.

## Outcome

`InterviewReviewHttpBrowserTests.setUpClass` installs isolated Flask, identity,
provider, logging, local-server, Playwright, and Chromium resources and
registers each restore with `addClassCleanup` immediately after the resource is
acquired. unittest therefore restores that state when a later setup step fails,
even though it skips `tearDownClass`. Server cleanup is registered before
`thread.start`, and shutdown does not wait on a thread that never started. One
cleanup exception does not prevent remaining cleanups.

Focused regressions prove a mocked Chromium launch failure still stops
Playwright and restores configuration, limiter, logging, and identity/provider
patches, and that remaining class cleanups continue after one cleanup failure.
The dedicated runner still pins exactly one HTTP method.

## Independent review

Read-only reviewer `agent:cursor-sol-interview-review-http-isolation-001`
independently re-ran the nine focused tests and the dedicated browser runner
against exact candidate `a9e20b0bb343fb75737e7f3bd9944af13d7edcb9` and returned
PASS with no blockers. Independently reproduced:

- Focused suite: 9 run, 9 passed, 0 skipped, 0 failures, 0 errors.
- Dedicated runner:
  `REVIEW_HTTP_BROWSER_SUMMARY={"discovered": 1, "errors": 0, "executed": 1, "expected": 1, "expected_failures": 0, "failures": 0, "passed": 1, "skipped": 0, "status": "pass", "tests_run": 1, "unexpected_successes": 0}`

This receipt and evidence file are the only post-review repository tail.

## Release truth

This is local synthetic Flask plus provider-stub proof plus setup-isolation
correction. It is not live AI, Easy Auth, two-member SQL, deployment, required
Azure CI for the dedicated runner, or full Interview proof. Deployment remains
withheld.
