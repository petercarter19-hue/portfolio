# PS-ASK-PETE-DEADLINE-TEST-002 evidence

Routine, self-reviewed, test-only. Routed by the Claude site manager as the
same-class follow-up of PS-ASK-PETE-DEADLINE-TEST-001: after a second
wall-clock flake of the same kind, fix the choke point. Five more tests in
`tests/ask_pete/test_live_foundry.py` gave the request a 30-50 ms real-time
deadline and expected it to expire while the worker was blocked at a specific
point; a GC pause or slow agent can spend that window first. The source search
found this pattern in no other test module.

The first baseline command injects a 300 ms pause before work submission and
before source loading, simulating that pause for all six deadline tests.

```package-acceptance-json
{
  "schema_version": 1,
  "package": "PS-ASK-PETE-DEADLINE-TEST-002",
  "plan_sha": "079eeeb83015e200bbff0891328a809e09391ee1",
  "baseline": [
    {
      "command": "python -B -c \"import sys,time,unittest;from unittest.mock import patch;from services.ask_pete import runtime as r,deadline as d;c=r._catalog;s=d._POOL.submit;patch.object(r,'_catalog',side_effect=lambda root:(time.sleep(.3),c(root))[1]).start();patch.object(d._POOL,'submit',side_effect=lambda w:(time.sleep(.3),s(w))[1]).start();m='tests.ask_pete.test_live_foundry.';n=['LiveFoundryTests.test_generation_timeout_cannot_retry','LiveFoundryTests.test_slow_credential_returns_by_deadline_and_never_starts_late_post','TelemetryTests.test_deadline_terminal_remains_unknown_with_late_worker_events','TelemetryTests.test_stalled_event_sink_is_marked_late_when_terminal_writes_first','TelemetryTests.test_real_logger_formats_late_at_write_after_stalled_info_call','DeadlineCapacityTests.test_abandoned_work_retains_slot_until_real_completion'];t=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromName(m+x) for x in n);sys.exit(not unittest.TextTestRunner(verbosity=2).run(t).wasSuccessful())\"",
      "exit_code": 1,
      "observation": "FAILED (failures=4) in 3 of 3 runs: test_generation_timeout_cannot_retry, test_slow_credential_returns_by_deadline_and_never_starts_late_post, test_stalled_event_sink_is_marked_late_when_terminal_writes_first and test_real_logger_formats_late_at_write_after_stalled_info_call each fail because the 30-50 ms wall-clock deadline expires before the worker reaches the point under test. The PS-ASK-PETE-DEADLINE-TEST-001 test passes. test_abandoned_work_retains_slot_until_real_completion passes this injection but still uses a 40 ms wall-clock deadline."
    },
    {
      "command": "python -B -m unittest tests.ask_pete.test_live_foundry",
      "exit_code": 0,
      "observation": "Ran 28 tests OK on a fast local machine."
    }
  ],
  "criteria": [
    {
      "id": "no-wall-clock-deadlines",
      "expected": "No test in tests/ask_pete/test_live_foundry.py builds a request deadline from wall-clock seconds. All six deadline tests use one shared helper whose deadline expires only once a named test event is set, and run_bounded's bounded wait still really times out.",
      "verification": "Source search of the module for RequestDeadline(monotonic() + ...), RequestDeadline.start(<seconds>) and original_start(...) finds none; the pause-injection baseline command passes; a run_bounded probe shows the timeout is a real concurrent.futures TimeoutError."
    },
    {
      "id": "stable-under-load",
      "expected": "The six deadline tests pass every time, both normally and under heavy CPU load with frequent garbage collection.",
      "verification": "200 in-process loops of the six tests normally and 200 under 2x-CPU busy-loop processes with gc.set_threshold(50, 5, 5), plus a control run of main's version under the same harness."
    },
    {
      "id": "assertions-kept",
      "expected": "Every behavioral assertion of the six tests is kept. A wall-clock bound or sleep is replaced only by an event-ordered check that proves the same property.",
      "verification": "Self-review of the full diff, listing each replaced timing construct and its event-ordered equivalent."
    },
    {
      "id": "test-only",
      "expected": "Only tests/ask_pete/test_live_foundry.py changes outside the package's claim, receipt and evidence; no product code, fake providers only, no deployment.",
      "verification": "git diff --name-only against the activation main SHA, the full module passing, and a full local discover compared with main."
    }
  ],
  "candidate_sha": "c501e20116d8b7d1ee2a7723acb3a2e16302e21d",
  "checks": [
    {
      "criterion_id": "no-wall-clock-deadlines",
      "result": "pass",
      "kind": "automated",
      "candidate_sha": "c501e20116d8b7d1ee2a7723acb3a2e16302e21d",
      "source_ref": "local run at c501e201: the 300 ms pause-injection baseline command",
      "observed": "Exit 0, 6 tests OK. The same command failed 4 tests in 3 of 3 runs on main 07dfac74.",
      "resolves_baseline_command": "python -B -c \"import sys,time,unittest;from unittest.mock import patch;from services.ask_pete import runtime as r,deadline as d;c=r._catalog;s=d._POOL.submit;patch.object(r,'_catalog',side_effect=lambda root:(time.sleep(.3),c(root))[1]).start();patch.object(d._POOL,'submit',side_effect=lambda w:(time.sleep(.3),s(w))[1]).start();m='tests.ask_pete.test_live_foundry.';n=['LiveFoundryTests.test_generation_timeout_cannot_retry','LiveFoundryTests.test_slow_credential_returns_by_deadline_and_never_starts_late_post','TelemetryTests.test_deadline_terminal_remains_unknown_with_late_worker_events','TelemetryTests.test_stalled_event_sink_is_marked_late_when_terminal_writes_first','TelemetryTests.test_real_logger_formats_late_at_write_after_stalled_info_call','DeadlineCapacityTests.test_abandoned_work_retains_slot_until_real_completion'];t=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromName(m+x) for x in n);sys.exit(not unittest.TextTestRunner(verbosity=2).run(t).wasSuccessful())\""
    },
    {
      "criterion_id": "no-wall-clock-deadlines",
      "result": "pass",
      "kind": "automated",
      "candidate_sha": "c501e20116d8b7d1ee2a7723acb3a2e16302e21d",
      "source_ref": "grep -nE 'monotonic|sleep|original_start|RequestDeadline\\(|RequestDeadline\\.start\\([^)]' tests/ask_pete/test_live_foundry.py at c501e201, plus a run_bounded cause probe over the six tests",
      "observed": "No wall-clock deadline, sleep or monotonic use remains in the module; deadline_expiring_once is defined once and used by all six deadline tests. In each test the request's AskPeteDeadlineError is caused by a real concurrent.futures TimeoutError from run_bounded's bounded wait; the capacity test's second call is the expected occupied refusal on a real 20 s deadline."
    },
    {
      "criterion_id": "stable-under-load",
      "result": "pass",
      "kind": "automated",
      "candidate_sha": "c501e20116d8b7d1ee2a7723acb3a2e16302e21d",
      "source_ref": "local stress6 harness at c501e201: 200 loops of the six tests normal, then 200 under 64 busy-loop processes on 32 cores with gc.set_threshold(50, 5, 5)",
      "observed": "0 failures in 1200 test runs normally (32.6 s) and 0 in 1200 under load (185.0 s). Control: main 07dfac74's file under the same load harness failed 38 of 1200 (generation timeout 27, real logger 4, slow credential 4, stalled sink 3)."
    },
    {
      "criterion_id": "assertions-kept",
      "result": "pass",
      "kind": "automated",
      "candidate_sha": "c501e20116d8b7d1ee2a7723acb3a2e16302e21d",
      "source_ref": "git diff 079eeeb8..c501e201 -- tests/ask_pete/test_live_foundry.py",
      "observed": "Every behavioral assertion is unchanged. Two timing constructs were replaced by event-ordered equivalents: the fake transport's 70 ms sleep now blocks on an event until the response is back (still exactly one transport call, no retry), and the 0.8 s elapsed bound is now a check that the credential stub had not returned when the response arrived (the response did not wait for it)."
    },
    {
      "criterion_id": "test-only",
      "result": "pass",
      "kind": "automated",
      "candidate_sha": "c501e20116d8b7d1ee2a7723acb3a2e16302e21d",
      "source_ref": "git diff --name-only 07dfac74 c501e201; python -B -m unittest tests.ask_pete.test_live_foundry; python -B -m unittest discover -s tests -q at c501e201",
      "observed": "Only tests/ask_pete/test_live_foundry.py and this evidence file changed. The module ran 28 tests OK. The full local discover ran 7926 tests; its 15 failures and 11 errors are the same set as the PS-ASK-PETE-DEADLINE-TEST-001 run, each on the 2026-10-09 local-only baseline or failing identically on main, and none is in Ask Pete."
    }
  ]
}
```
