# PS-ASK-PETE-DEADLINE-TEST-001 evidence

Routine, self-reviewed, test-only. `TelemetryTests.test_deadline_terminal_remains_unknown_with_late_worker_events`
used a 50 ms wall-clock deadline. On a slow CI agent (PR 1394 builds 4668, 4669
and 4671, a change with no Ask Pete code) it expired during source loading, so
the terminal record read `last_stage` `sources` instead of `credential`. The
MVP1 builder session measured a full GC pass at about 39 ms after CI-style
discovery, which fits a repeatable expiry inside that window.

The first baseline command injects a 300 ms source-loading delay and reproduces
the CI failure exactly. The second is the plain focused run, which passes on a
fast machine.

```package-acceptance-json
{
  "schema_version": 1,
  "package": "PS-ASK-PETE-DEADLINE-TEST-001",
  "plan_sha": "e32638e31088970050157b209975ba1d3484293c",
  "baseline": [
    {
      "command": "python -B -c \"import sys,time,unittest;from unittest.mock import patch;from services.ask_pete import runtime as r;c=r._catalog;p=patch.object(r,'_catalog',side_effect=lambda root:(time.sleep(.3),c(root))[1]);p.start();s=unittest.defaultTestLoader.loadTestsFromName('tests.ask_pete.test_live_foundry.TelemetryTests.test_deadline_terminal_remains_unknown_with_late_worker_events');sys.exit(not unittest.TextTestRunner().run(s).wasSuccessful())\"",
      "exit_code": 1,
      "observation": "FAILED: Tuples differ: ('unavailable', 'deadline_exceeded', 'sources') != ('unavailable', 'deadline_exceeded', 'credential'), the same failure as PR 1394 build 4668."
    },
    {
      "command": "python -B -m unittest tests.ask_pete.test_live_foundry.TelemetryTests.test_deadline_terminal_remains_unknown_with_late_worker_events",
      "exit_code": 0,
      "observation": "OK on a fast local machine; the pass depends on reaching the credential stub within 50 ms of real time."
    }
  ],
  "criteria": [
    {
      "id": "credential-stage-expiry",
      "expected": "The test deadline expires only on its first check after the worker enters the credential stub, independent of wall-clock time, so the terminal record is always (unavailable, deadline_exceeded, credential).",
      "verification": "The source-delay baseline command passes on the candidate, and the focused test passes 200 times in a row normally and 200 times under full CPU load."
    },
    {
      "id": "late-events-and-transport",
      "expected": "The assertions that late worker events never change the single terminal record, that a late generation event without usage arrives, and that the transport is never called are kept unchanged.",
      "verification": "Diff review of the test plus the passing runs above."
    },
    {
      "id": "test-only",
      "expected": "Only tests/ask_pete/test_live_foundry.py changes outside the package's claim, receipt and evidence; no product code, fake providers only, no deployment.",
      "verification": "git diff --name-only against the activation main SHA, and the full test module passing."
    }
  ],
  "candidate_sha": "f6f9235633ecea0bd3d3d7078b4ca8f8782a058d",
  "checks": [
    {
      "criterion_id": "credential-stage-expiry",
      "result": "pass",
      "kind": "automated",
      "candidate_sha": "f6f9235633ecea0bd3d3d7078b4ca8f8782a058d",
      "source_ref": "local run at f6f92356: the 300 ms source-delay baseline command",
      "observed": "Exit 0: with source loading slowed by 300 ms the terminal record is (unavailable, deadline_exceeded, credential); main fails the same command with last_stage sources.",
      "resolves_baseline_command": "python -B -c \"import sys,time,unittest;from unittest.mock import patch;from services.ask_pete import runtime as r;c=r._catalog;p=patch.object(r,'_catalog',side_effect=lambda root:(time.sleep(.3),c(root))[1]);p.start();s=unittest.defaultTestLoader.loadTestsFromName('tests.ask_pete.test_live_foundry.TelemetryTests.test_deadline_terminal_remains_unknown_with_late_worker_events');sys.exit(not unittest.TextTestRunner().run(s).wasSuccessful())\""
    },
    {
      "criterion_id": "credential-stage-expiry",
      "result": "pass",
      "kind": "automated",
      "candidate_sha": "f6f9235633ecea0bd3d3d7078b4ca8f8782a058d",
      "source_ref": "local stress harness at f6f92356: 200 in-process runs normal, then 200 under 64 CPU burners on 32 cores with gc threshold (50, 5, 5)",
      "observed": "0 of 200 failures normally (5.6 s) and 0 of 200 under load (49.7 s). Control: main's test under the same load harness failed 8 of 200, with last_stage request (6) and currentness (2)."
    },
    {
      "criterion_id": "late-events-and-transport",
      "result": "pass",
      "kind": "automated",
      "candidate_sha": "f6f9235633ecea0bd3d3d7078b4ca8f8782a058d",
      "source_ref": "git diff ec2a49fd..f6f92356 -- tests/ask_pete/test_live_foundry.py, plus a run_bounded probe at f6f92356",
      "observed": "The terminal tuple, single request record, late generation event without usage, and transport.post.assert_not_called assertions are byte-unchanged. A probe wrapping run_bounded shows the request's AskPeteDeadlineError is caused by a real concurrent.futures TimeoutError, the same path as the original test."
    },
    {
      "criterion_id": "test-only",
      "result": "pass",
      "kind": "automated",
      "candidate_sha": "f6f9235633ecea0bd3d3d7078b4ca8f8782a058d",
      "source_ref": "git diff --name-only ec2a49fd f6f92356; python -B -m unittest tests.ask_pete.test_live_foundry; python -B -m unittest discover -s tests -q at f6f92356",
      "observed": "Only tests/ask_pete/test_live_foundry.py and this evidence file changed. The module ran 28 tests OK. The full local discover ran 7881 tests; its 15 failures and 11 errors are all outside Ask Pete, each is on the 2026-10-09 local-only baseline or fails identically on main bd07b1ee (IPv6 loopback on local Python, missing local av module, three Playwright browser tests), and none is in the changed module."
    }
  ]
}
```
