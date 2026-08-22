"""Execute the full 40-fixture parity replay and emit a machine-readable
zero-difference report (consolidated B6).

Runs the real parity suite — every fixture replays through the live
Flask application (Flask-Limiter active) against the corrected candidate
— and records, per fixture, pass/fail plus the environment the replay
executed in (interpreter, Flask stack versions, and their congruence
with the locked external runtime closure).
"""

import importlib.metadata
import json
import platform
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


def main():
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromName("tests.interview_ai.test_parity_replay")

    outcomes = {}

    class Collector(unittest.TestResult):
        def addSubTest(self, test, subtest, err):
            super().addSubTest(test, subtest, err)
            params = dict(subtest.params) if subtest.params else {}
            fixture = params.get("fixture", str(subtest))
            outcomes[fixture] = "pass" if err is None else "FAIL"

        def addFailure(self, test, err):
            super().addFailure(test, err)
            outcomes[str(test)] = "FAIL"

        def addError(self, test, err):
            super().addError(test, err)
            outcomes[str(test)] = "ERROR"

    result = Collector()
    suite.run(result)

    lock = json.loads(
        (ROOT / "prompts" / "interview" / "contracts"
         / "external-runtime-1.json").read_text(encoding="utf-8")
    )
    locked_versions = {
        record["name"]: record["version"] for record in lock["distributions"]
    }
    flask_stack = {}
    for distribution in ("flask", "flask-limiter", "werkzeug", "limits"):
        installed = importlib.metadata.version(distribution)
        flask_stack[distribution] = {
            "installed": installed,
            "locked": locked_versions.get(distribution),
            "congruent": installed == locked_versions.get(distribution),
        }

    registry = json.loads(
        (ROOT / "prompts" / "interview" / "control"
         / "registry.json").read_text(encoding="utf-8")
    )
    failures = [name for name, value in outcomes.items() if value != "pass"]
    report = {
        "result": "pass" if not failures and outcomes else "FAIL",
        "fixtures_replayed": len(outcomes),
        "fixtures_differing": len(failures),
        "differing": sorted(failures),
        "release_set_id":
            registry["active_release_set"]["interview_release_set_id"],
        "environment": {
            "python": platform.python_version(),
            "flask_stack": flask_stack,
        },
        "fixtures": {name: outcomes[name] for name in sorted(outcomes)},
    }
    print(json.dumps(report, indent=1, sort_keys=True))
    return 0 if report["result"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
