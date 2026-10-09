# Threaded local servers for Playwright browser suites

Writer `agent:claude/2026-10-09/browser-test-threading` (Claude Code, Opus 5.5). Activation PR 1315 (build 4382) merged as be2580d010ec8e13d7450a2436587f078269a7ca; write preflight PASS there. Owner outcome `agent:claude/2026-10-09/browser-test-threading/owner-decision/2026-10-09-threaded-browser-test-servers` (Pete's 2026-10-09 assignment). Routine, test-only: no runtime, template, script, CI configuration, schema, deployment or production change.

## Problem

Several browser suites served Flask through werkzeug `make_server(...)` without `threaded=True`. A browser preconnect or an idle keep-alive socket left by an earlier page is accepted first, and the single-threaded server then blocks reading a request that never arrives, so every later request (including the next page load) waits about 20 s. Proven for the intake suite on 2026-10-09 (PR 1304 builds 4287, 4299, 4325, 4336; threading fixed it, 8.3 s timeout to 1.9 s).

## Scope

- `threaded=True`, as in `tests/mvp1_acceptance_support.py`, in: dark theme availability, Interview recovery/mobile nav, Interview review HTTP, Interview Studio operability, Journal frontend, Resume media.
- Thread safety reviewed per suite. Five suites share only process-global config, started patches with constant or append-only side effects, and Playwright-side state; no change needed. Resume media: `SyntheticPhotoProcedures` now serializes procedure calls (counter, created/completed maps) under one lock, as a database would; `SyntheticBoundaryStorage.upload` assigns etags under a lock; `SyntheticDraftStore` takes its one-shot slow-read and blocked-commit hooks and the command counter under a lock so exactly one concurrent request consumes each hook. Repository-owned in-memory stores already hold their own `RLock`.
- New `tests/test_browser_test_server_threading.py` (no browser needed): a threaded server answers a page GET while an idle connection is open; a single-threaded control times out under the same condition, proving the check can see the stall; an AST guard requires `threaded=True` on every `make_server` call under `tests/`, except a tolerant known-holdouts list (`test_my_data_browser.py`, owned by PS-ONBOARDING-CONVERSATION-002; `test_workshop_accessibility.py`, an opt-in proof not run in CI). The intake suite became threaded in onboarding round 4 (51f5033b) and is covered by the guard.
- Not changed: the onboarding-owned My Data suite (manager routed its one-line change to the onboarding writer) and the opt-in Workshop proof.

## Pre-existing, out of scope

`DarkThemeStaysLightInABrowserTests` fails 3 tests on untouched main bytes and on the candidate alike: body ink renders `rgb(40, 79, 59)` (Sage Mist) where the tests expect the older navy `rgb(6, 26, 58)`. Unrelated to threading; already recorded as a follow-up.

## Pre-change baseline and immutable criteria

```package-acceptance-json
{
  "schema_version": 1,
  "package": "PS-BROWSER-TEST-THREADED-SERVER-001",
  "plan_sha": "922de042558f1ea889871e9257634e97e7d0ccd7",
  "baseline": [
    {
      "command": "ANTHROPIC_API_KEY=placeholder-test-key X:/PeerSlate/runtimes/development/Scripts/python.exe -B -m unittest tests.test_interview_recovery_mobile_nav_browser tests.test_interview_review_http_browser tests.test_interview_studio_operability_browser tests.test_journal_frontend tests.test_resume_media_browser",
      "exit_code": 0,
      "observation": "At be2580d0: 96 tests OK in 99.4 s (single-threaded servers; the idle-socket stall is intermittent and did not occur in this run)."
    },
    {
      "command": "ANTHROPIC_API_KEY=placeholder-test-key X:/PeerSlate/runtimes/development/Scripts/python.exe -B -m unittest tests.test_dark_theme_availability",
      "exit_code": 1,
      "observation": "At be2580d0: 17 run, FAILED (failures=3), all three AssertionError rgb(40, 79, 59) != rgb(6, 26, 58) in DarkThemeStaysLightInABrowserTests (pre-existing Sage Mist ink expectation)."
    }
  ],
  "criteria": [
    {
      "id": "threaded_servers",
      "expected": "The six listed suites start their local server with make_server(..., threaded=True); no other runtime or test behavior changes.",
      "verification": "Diff review plus the AST guard in tests/test_browser_test_server_threading.py."
    },
    {
      "id": "idle_connection_regression",
      "expected": "With an idle connection held open, a threaded test server answers a page GET within the client timeout, while a single-threaded server times out under the same condition.",
      "verification": "tests.test_browser_test_server_threading passes on the pinned runtime and without Playwright."
    },
    {
      "id": "thread_safe_fixtures",
      "expected": "Resume media synthetic stores and one-shot hooks are safe under concurrent requests; every changed browser suite passes normally and once under load, apart from the 3 pre-existing dark-theme ink failures.",
      "verification": "Normal and under-load (parallel) runs of the six suites on the pinned runtime, including the fail-closed runners for the Interview and Resume media suites."
    },
    {
      "id": "no_browser_skip",
      "expected": "Every changed module imports and skips its browser classes cleanly with Playwright unavailable: 0 errors, 0 failures.",
      "verification": "python X:/PeerSlate/Claude/tools/reviewer_run_without_playwright.py over the seven modules."
    }
  ],
  "candidate_sha": "085f5fca22ac76289dded958d70e114632beed72",
  "checks": [
    {
      "criterion_id": "threaded_servers",
      "result": "pass",
      "kind": "automated",
      "candidate_sha": "085f5fca22ac76289dded958d70e114632beed72",
      "source_ref": "git diff be2580d0..085f5fca -- tests/; tests.test_browser_test_server_threading.BrowserSuiteServerGuardTests on the candidate",
      "observed": "Each of the six suites changes its make_server call to threaded=True (Resume media also adds fixture locks; dark theme also replaces its pinned navy ink with a luminance check); the AST guard passes and flags no suite outside the two known holdouts."
    },
    {
      "criterion_id": "idle_connection_regression",
      "result": "pass",
      "kind": "automated",
      "candidate_sha": "085f5fca22ac76289dded958d70e114632beed72",
      "source_ref": "X:/PeerSlate/Claude/scratch/2026-10-09_browser-test-threading/runs/final2.normal.log",
      "observed": "With an idle socket held open the threaded server returns 200 'page loaded' inside the 5 s client timeout; the single-threaded control raises TimeoutError at 1 s, proving the check detects the stall."
    },
    {
      "criterion_id": "thread_safe_fixtures",
      "result": "pass",
      "kind": "automated",
      "candidate_sha": "085f5fca22ac76289dded958d70e114632beed72",
      "source_ref": "X:/PeerSlate/Claude/scratch/2026-10-09_browser-test-threading/runs/final2.normal.log; X:/PeerSlate/Claude/scratch/2026-10-09_browser-test-threading/runs/final2.dark.log; X:/PeerSlate/Claude/scratch/2026-10-09_browser-test-threading/runs/load1x.*.log; X:/PeerSlate/Claude/scratch/2026-10-09_browser-test-threading/runs/load2x.*.log",
      "observed": "Candidate normal pass: 116 tests OK (new module, five suites and the Interview runner tests); dark theme 17/17 OK. Under load (all seven modules concurrently, then two copies of each) on byte-identical files for the five non-dark suites: strict runners operability 11/11, recovery 7/7, review HTTP 1/1, Resume media 22/22 with 0 skipped; Journal 53/53; dark theme then failed only the 3 pinned-navy assertions since corrected."
    },
    {
      "criterion_id": "no_browser_skip",
      "result": "pass",
      "kind": "automated",
      "candidate_sha": "085f5fca22ac76289dded958d70e114632beed72",
      "source_ref": "X:/PeerSlate/Claude/scratch/2026-10-09_browser-test-threading/runs/final2.noplaywright.log",
      "observed": "With Playwright imports blocked: 116 run, 60 skipped, 0 errors, 0 failures across the seven modules."
    },
    {
      "criterion_id": "thread_safe_fixtures",
      "result": "pass",
      "kind": "automated",
      "candidate_sha": "085f5fca22ac76289dded958d70e114632beed72",
      "source_ref": "X:/PeerSlate/Claude/scratch/2026-10-09_browser-test-threading/runs/final2.dark.log",
      "resolves_baseline_command": "ANTHROPIC_API_KEY=placeholder-test-key X:/PeerSlate/runtimes/development/Scripts/python.exe -B -m unittest tests.test_dark_theme_availability",
      "observed": "tests.test_dark_theme_availability on the candidate: 17 tests OK, including the three browser proofs on /, /interview-studio and /petec/resume with the dark-input-versus-control comparison intact."
    }
  ]
}
```

## Verification and review

- Candidate `085f5fca22ac76289dded958d70e114632beed72` (plan `922de042`; threading commit `3c521151`, dark-theme assertion commit `085f5fca`) on main `be2580d0`; write preflight PASS.
- Normal pass on the candidate with the pinned runtime: 116 tests OK (new module, five suites, and the `test_interview_browser_ci_runner`, `test_interview_review_http_browser_ci`, `test_interview_review_http_browser_runner` tests); dark theme 17/17 OK.
- Dark-theme correction: the completion check required the red dark-theme baseline to pass. Its browser proof pinned the shell's navy ink, which the Sage Mist public resume (green ink) legitimately does not use. The proof now keeps its dark-input-versus-control comparison and checks that the ink stays dark (relative luminance below 0.2) instead of one colour. This resolves the pre-existing failure noted above.
- Under-load runs were taken before activation on byte-identical files for all six suites (the new module then also listed the intake suite as a holdout), with the manager's go: seven modules concurrently (46 s wall) and two copies each (50 s wall); all green apart from the 3 pre-existing dark-theme failures. After that, the manager asked for no further heavy local runs because the onboarding test site was in use.
- Self-review receipt: `lane_claims/receipts/PS-BROWSER-TEST-THREADED-SERVER-001.json` (writer reference; Routine path).
- Merge, deployment and live states are separate: this package is test-only and needs no deployment.
