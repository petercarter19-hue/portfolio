# PS-INTERVIEW-REVIEW-HTTP-CI-001 candidate evidence

Activation PR 984 squash-merged as
`e8f9488ed4b85bb95aa77e9f63b7f60a597387c0`. The active Bounded claim assigns
implementation to sole writer
`session:cursor-grok-interview-review-http-001`; production authority is
withheld.

Exact reviewed candidate
`9efcea8e7e7df3316864712cbc45093a4f8eb5c0` changes only:

- `azure-pipelines.yml`
- `tests/test_interview_review_http_browser_ci.py`

Interview production runtime, identity, storage, schema, the existing eleven
browser-test bodies, and `scripts/run_interview_review_http_browser.py` are
byte-identical to the merged activation base.

## Outcome

`InterviewStudioBrowserCI` keeps the existing pinned browser-CI install
(`requirements.txt` plus `requirements-browser-ci.txt`, Playwright Chromium,
`PLAYWRIGHT_BROWSERS_PATH`, and `ANTHROPIC_API_KEY=test-key-for-ci-only`) and
adds a fail-closed step:

`python scripts/run_interview_review_http_browser.py`

The existing eleven-test runner remains in that job. Ordinary backend
`python -m unittest discover -s tests -q` remains in `BuildJob` and is not
duplicated in the browser job. The pipeline contract test proves the Review
HTTP runner cannot be omitted, disabled, conditioned off, invoked as unittest
directly, or allowed to fail with `continueOnError` / `|| true`.

Main branch policy `CI must pass` is enabled and blocking against pipeline
definition 1 (`azure-pipelines.yml`). This job is part of that required Build
stage.

## Independent review

Read-only reviewer `agent:cursor-sol-interview-review-http-ci-001`
independently re-ran focused tests and the dedicated browser runner against
exact candidate `9efcea8e7e7df3316864712cbc45093a4f8eb5c0` and returned PASS
with no blockers. Independently reproduced:

- Focused suite: 17 run, 17 passed, 0 skipped, 0 failures, 0 errors.
- Dedicated runner:
  `REVIEW_HTTP_BROWSER_SUMMARY={"discovered": 1, "errors": 0, "executed": 1, "expected": 1, "expected_failures": 0, "failures": 0, "passed": 1, "skipped": 0, "status": "pass", "tests_run": 1, "unexpected_successes": 0}`

This receipt and evidence file are the only post-review repository tail.

## Release truth

This wires the local synthetic Flask plus provider-stub Review HTTP browser
proof onto the required Azure PR pipeline. It is not live AI, Easy Auth,
two-member SQL, production deployment, or paid-provider proof. Azure log
counts for the new runner must be recorded from the implementation PR run;
local results are not merge-gate proof.
