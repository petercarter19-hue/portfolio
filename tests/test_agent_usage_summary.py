import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "agent_usage_summary.py"
SPEC = importlib.util.spec_from_file_location("agent_usage_summary", SCRIPT)
usage_summary = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = usage_summary
SPEC.loader.exec_module(usage_summary)


SESSION_A = "11111111-1111-4111-8111-111111111111"
SESSION_B = "22222222-2222-4222-8222-222222222222"


def metric(input_tokens, cached, output, reasoning=0, cache_write=0):
    return {
        "input_tokens": input_tokens,
        "cached_input_tokens": cached,
        "cache_write_input_tokens": cache_write,
        "output_tokens": output,
        "reasoning_output_tokens": reasoning,
        "total_tokens": input_tokens + output,
    }


def meta(session_id):
    return {"type": "session_meta", "payload": {"id": session_id}}


def context(turn_id, model, effort="high"):
    return {
        "type": "turn_context",
        "payload": {"turn_id": turn_id, "model": model, "effort": effort},
    }


def canonical(session_id, turn_id, response_id, values, cumulative):
    return {
        "type": "token_usage_record",
        "payload": {
            "thread_id": session_id,
            "session_id": session_id,
            "turn_id": turn_id,
            "response_id": response_id,
            "usage": values,
            "thread_token_usage": cumulative,
        },
    }


def legacy(cumulative):
    return {
        "type": "event_msg",
        "payload": {
            "type": "token_count",
            "info": {
                "total_token_usage": cumulative,
                "last_token_usage": cumulative,
            },
        },
    }


class UsageSummaryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def write(self, name, records):
        path = self.root / name
        path.write_text(
            "".join(json.dumps(item) + "\n" for item in records),
            encoding="utf-8",
        )
        return path

    def test_canonical_records_win_and_reasoning_is_not_double_counted(self):
        turn_a = "turn-a"
        first = metric(100, 40, 30, 10, cache_write=7)
        second = metric(80, 20, 25, 5, cache_write=3)
        records = [
            meta(SESSION_A),
            context(turn_a, "gpt-5.6-sol"),
            canonical(SESSION_A, turn_a, "response-1", first, first),
            legacy(first),  # mirror: must never be added
            context("turn-b", "gpt-6-astra", "medium"),
            # A repeated response remains the same record even after the
            # active turn/model context changes.
            canonical(SESSION_A, "turn-b", "response-1", first, first),
            # A lower cumulative counter is diagnostic only; response usage
            # remains the canonical accounting source.
            canonical(SESSION_A, "turn-b", "response-2", second, second),
        ]
        records[0]["timestamp"] = "2026-09-06T10:00:00Z"
        records[-1]["timestamp"] = "2026-09-06T10:02:30+00:00"
        records[1]["payload"]["service_tier"] = "priority"
        path = self.write(
            "a.jsonl",
            records,
        )
        report = usage_summary.summarize(
            [usage_summary.SessionSelection(SESSION_A, path)]
        )
        self.assertEqual("available", report["status"])
        self.assertEqual(180, report["usage"]["input_tokens"])
        self.assertEqual(60, report["usage"]["cached_input_tokens"])
        self.assertEqual(
            10, report["usage"]["cache_write_input_tokens_included_in_input"]
        )
        self.assertEqual(120, report["usage"]["fresh_input_tokens"])
        self.assertEqual(55, report["usage"]["output_tokens"])
        self.assertEqual(
            15, report["usage"]["reasoning_output_tokens_included_in_output"]
        )
        self.assertEqual(235, report["usage"]["total_tokens"])
        session = report["sessions"][0]
        self.assertEqual("token_usage_record", session["source"])
        self.assertEqual(1, session["duplicate_records_ignored"])
        self.assertEqual(1, session["cumulative_resets_observed"])
        self.assertEqual(1, session["model_changes_observed"])
        self.assertEqual(2, len(session["models"]))
        self.assertEqual(150.0, session["elapsed_seconds_observed"])
        self.assertEqual(["priority"], session["service_tiers_observed"])
        self.assertEqual("unavailable", session["speeds_observed"])
        self.assertEqual(
            "unavailable", report["bounded_evidence"]["known_waiting"]["status"]
        )

    def test_legacy_cumulative_fallback_counts_segments_and_duplicates_once(self):
        a = metric(100, 25, 20, 4)
        b = metric(160, 40, 35, 7)
        reset = metric(30, 10, 5, 1)
        path = self.write(
            "legacy.jsonl",
            [
                meta(SESSION_A),
                context("turn-a", "gpt-5.6-sol"),
                legacy(a),
                legacy(a),
                legacy(b),
                context("turn-b", "gpt-6-astra", "medium"),
                legacy(reset),
            ],
        )
        report = usage_summary.summarize(
            [usage_summary.SessionSelection(SESSION_A, path)]
        )
        session = report["sessions"][0]
        self.assertIn("cumulative_fallback", session["source"])
        self.assertEqual(190, session["usage"]["input_tokens"])
        self.assertEqual(50, session["usage"]["cached_input_tokens"])
        self.assertEqual(40, session["usage"]["output_tokens"])
        self.assertEqual(1, session["duplicate_records_ignored"])
        self.assertEqual(1, session["cumulative_resets_observed"])
        self.assertEqual(1, session["model_changes_observed"])

    def test_explicit_root_and_child_are_each_selected_once(self):
        child_record = canonical(
            SESSION_B, "b", "rb", metric(20, 8, 3), metric(20, 8, 3)
        )
        child_record["payload"]["session_id"] = SESSION_A
        path_a = self.write(
            "a.jsonl",
            [
                meta(SESSION_A),
                context("a", "gpt-6-astra", "medium"),
                canonical(SESSION_A, "a", "ra", metric(10, 4, 2), metric(10, 4, 2)),
            ],
        )
        path_b = self.write(
            "b.jsonl",
            [
                meta(SESSION_B),
                context("b", "gpt-5.6-sol", "high"),
                child_record,
            ],
        )
        report = usage_summary.summarize(
            [
                usage_summary.SessionSelection(SESSION_A, path_a),
                usage_summary.SessionSelection(SESSION_B, path_b),
            ]
        )
        self.assertEqual(2, report["sessions_selected"])
        self.assertEqual(30, report["usage"]["input_tokens"])
        self.assertEqual(SESSION_A, report["sessions"][1]["root_session_id"])
        with self.assertRaisesRegex(
            usage_summary.UsageSummaryError, "duplicate_session_selection"
        ):
            usage_summary.summarize(
                [
                    usage_summary.SessionSelection(SESSION_A, path_a),
                    usage_summary.SessionSelection(SESSION_A, path_a),
                ]
            )

    def test_unavailable_and_hostile_values_are_secret_safe(self):
        sentinel = "REDACT-ME"
        hostile = metric(1, 0, 1)
        hostile["input_tokens"] = sentinel
        path = self.write(
            "hostile.jsonl",
            [
                meta(SESSION_A),
                context("turn-a", sentinel),
                canonical(SESSION_A, "turn-a", sentinel, hostile, metric(1, 0, 1)),
                {"type": "response_item", "payload": {"text": sentinel}},
            ],
        )
        report = usage_summary.summarize(
            [usage_summary.SessionSelection(SESSION_A, path)]
        )
        encoded = json.dumps(report)
        self.assertEqual("unavailable", report["status"])
        self.assertNotIn(sentinel, encoded)
        self.assertNotIn(str(path), encoded)
        self.assertEqual("invalid_usage_record", report["sessions"][0]["reason"])

    def test_invalid_utf8_is_structured_unavailable_without_content(self):
        path = self.root / "invalid.jsonl"
        path.write_bytes(b'{' + bytes([0xFF]) + b'}\n')

        report = usage_summary.summarize(
            [usage_summary.SessionSelection(SESSION_A, path)]
        )

        self.assertEqual("unavailable", report["status"])
        self.assertEqual("invalid_jsonl", report["sessions"][0]["reason"])
        self.assertNotIn(str(path), json.dumps(report))

        completed = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--session",
                f"{SESSION_A}={path}",
                "--format",
                "json",
            ],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(2, completed.returncode)
        self.assertNotIn("Traceback", completed.stderr)
        self.assertEqual(
            "invalid_jsonl", json.loads(completed.stdout)["sessions"][0]["reason"]
        )

    def test_missing_optional_counters_remain_unavailable_at_each_level(self):
        values = {
            "input_tokens": 10,
            "cached_input_tokens": 2,
            "output_tokens": 3,
            "total_tokens": 13,
        }
        path = self.write(
            "missing-optional.jsonl",
            [
                meta(SESSION_A),
                context("turn", "gpt-5.6-sol"),
                canonical(SESSION_A, "turn", "response", values, values),
            ],
        )

        report = usage_summary.summarize(
            [usage_summary.SessionSelection(SESSION_A, path)]
        )

        for usage in (
            report["usage"],
            report["sessions"][0]["usage"],
            report["sessions"][0]["models"][0]["usage"],
        ):
            self.assertEqual(
                "unavailable", usage["cache_write_input_tokens_included_in_input"]
            )
            self.assertEqual(
                "unavailable", usage["reasoning_output_tokens_included_in_output"]
            )
            self.assertEqual(13, usage["total_tokens"])
        rendered = usage_summary.render_text(report)
        self.assertIn("Cache-write input subset: unavailable", rendered)
        self.assertIn("Reasoning output subset (already included): unavailable", rendered)

    def test_cli_json_never_emits_selected_path(self):
        path = self.write("empty.jsonl", [meta(SESSION_A)])
        completed = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--session",
                f"{SESSION_A}={path}",
                "--format",
                "json",
            ],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(2, completed.returncode)
        self.assertNotIn(str(path), completed.stdout + completed.stderr)
        self.assertEqual(
            "token_usage_record_absent",
            json.loads(completed.stdout)["sessions"][0]["reason"],
        )

    def test_exact_id_discovery_requires_one_metadata_matching_file(self):
        nested = self.root / "sessions" / "2026" / "09" / "06"
        nested.mkdir(parents=True)
        path = nested / f"rollout-2026-09-06T10-00-00-{SESSION_A}.jsonl"
        path.write_text(
            "\n".join(
                json.dumps(item)
                for item in (
                    meta(SESSION_A),
                    context("turn", "gpt-5.6-sol"),
                    canonical(
                        SESSION_A,
                        "turn",
                        "response",
                        metric(10, 2, 1),
                        metric(10, 2, 1),
                    ),
                )
            )
            + "\n",
            encoding="utf-8",
        )
        selection = usage_summary._discover(SESSION_A, [self.root])
        self.assertEqual(path.resolve(), selection.path)
        report = usage_summary.summarize([selection])
        self.assertEqual("available", report["status"])

        duplicate_root = self.root / "archive"
        duplicate_root.mkdir()
        (duplicate_root / path.name).write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
        ambiguous = usage_summary._discover(SESSION_A, [self.root])
        self.assertEqual("ambiguous_session_file", ambiguous.selection_error)
        ambiguous_report = usage_summary.summarize([ambiguous])
        self.assertEqual("unavailable", ambiguous_report["status"])
        self.assertNotIn(str(path), json.dumps(ambiguous_report))

    def test_cli_text_shows_model_effort_and_honest_waiting(self):
        path = self.write(
            f"rollout-{SESSION_A}.jsonl",
            [
                meta(SESSION_A),
                context("turn", "gpt-5.6-sol", "high"),
                canonical(
                    SESSION_A,
                    "turn",
                    "response",
                    metric(10, 2, 1),
                    metric(10, 2, 1),
                ),
            ],
        )
        report = usage_summary.summarize(
            [usage_summary.SessionSelection(SESSION_A, path)]
        )
        rendered = usage_summary.render_text(report)
        self.assertIn("gpt-5.6-sol/high", rendered)
        self.assertIn("elapsed unavailable", rendered)
        self.assertIn("known waiting unavailable", rendered)


if __name__ == "__main__":
    unittest.main()
